from __future__ import annotations

import os
import signal
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from secrets import token_hex

from .exceptions import IndicatorParsingError, IndicatorValidationError
from .indicator_parser import normalize_text


MAX_INDICATOR_WORD_SIZE = 10 * 1024 * 1024
SUPPORTED_WORD_EXTENSIONS = {'.doc', '.docx'}


@dataclass(frozen=True, slots=True)
class PreparedIndicatorDocument:
    source_filename: str
    original_content: bytes
    docx_content: bytes


class IndicatorDocumentConverter:
    """Подготавливает старый бинарный DOC или DOCX для общего DOCX-парсера."""

    def prepare_upload(self, uploaded_file) -> PreparedIndicatorDocument:
        filename, content = self.read_upload(uploaded_file)
        return self.prepare_content(source_filename=filename, content=content)

    @staticmethod
    def read_upload(uploaded_file) -> tuple[str, bytes]:
        if uploaded_file is None:
            raise IndicatorValidationError('Файл не выбран.')

        filename = normalize_text(getattr(uploaded_file, 'name', ''))
        if not filename:
            raise IndicatorValidationError('Не удалось определить имя загруженного файла.')
        if len(filename) > 255:
            raise IndicatorValidationError('Имя файла Word не должно превышать 255 символов.')
        extension = Path(filename).suffix.casefold()
        if extension not in SUPPORTED_WORD_EXTENSIONS:
            raise IndicatorValidationError('Поддерживаются только файлы Word с расширением .doc или .docx.')

        try:
            content = uploaded_file.read()
        except Exception as exc:
            raise IndicatorValidationError('Не удалось прочитать загруженный файл.') from exc
        if not content:
            raise IndicatorValidationError('Загружен пустой файл.')
        if len(content) > MAX_INDICATOR_WORD_SIZE:
            raise IndicatorValidationError('Размер файла Word не должен превышать 10 МБ.')
        return filename, content

    def prepare_content(self, *, source_filename: str, content: bytes) -> PreparedIndicatorDocument:
        extension = Path(source_filename).suffix.casefold()
        docx_content = content if extension == '.docx' else self.convert_doc_bytes(
            content=content,
            source_filename=source_filename,
        )
        return PreparedIndicatorDocument(
            source_filename=source_filename,
            original_content=content,
            docx_content=docx_content,
        )

    def convert_doc_bytes(self, *, content: bytes, source_filename: str) -> bytes:
        temp_path = Path(tempfile.gettempdir()) / f'indicator-doc-{token_hex(12)}'
        if os.name == 'nt':
            temp_path.mkdir()
        else:
            temp_path.mkdir(mode=0o700)
        try:
            source_path = temp_path / 'source.doc'
            source_path.write_bytes(content)

            converter = shutil.which('soffice') or shutil.which('libreoffice')
            if converter:
                output_path = source_path.with_suffix('.docx')
                self._convert_with_libreoffice(converter, source_path, temp_path)
            elif os.name == 'nt' and shutil.which('powershell.exe'):
                output_path = temp_path / 'converted.docx'
                self._convert_with_microsoft_word(source_path, output_path)
            else:
                raise IndicatorParsingError(
                    'Для обработки .doc на сервере не найден LibreOffice. '
                    'Установите libreoffice-writer или используйте проектный Docker-образ.'
                )

            if not output_path.is_file() or output_path.stat().st_size == 0:
                raise IndicatorParsingError(
                    f'Не удалось преобразовать файл «{source_filename}» из .doc в .docx.'
                )
            return output_path.read_bytes()
        finally:
            self._remove_temp_directory(temp_path)

    @staticmethod
    def _remove_temp_directory(temp_path: Path) -> None:
        for delay in (0, 0.1, 0.3):
            if delay:
                time.sleep(delay)
            try:
                shutil.rmtree(temp_path)
                return
            except FileNotFoundError:
                return
            except OSError:
                continue
        shutil.rmtree(temp_path, ignore_errors=True)

    @staticmethod
    def _convert_with_libreoffice(converter: str, source_path: Path, output_dir: Path) -> None:
        env = os.environ.copy()
        env['HOME'] = str(output_dir)
        try:
            result = subprocess.run(
                [
                    converter,
                    '--headless',
                    '--convert-to',
                    'docx',
                    '--outdir',
                    str(output_dir),
                    str(source_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IndicatorParsingError('Не удалось запустить LibreOffice для обработки .doc.') from exc
        if result.returncode != 0:
            raise IndicatorParsingError('LibreOffice не смог преобразовать загруженный .doc-файл.')

    @staticmethod
    def _convert_with_microsoft_word(source_path: Path, output_path: Path) -> None:
        source_path = source_path.resolve()
        output_path = output_path.resolve()
        existing_word_process_ids = IndicatorDocumentConverter._get_word_process_ids()
        script_path = source_path.parent / 'convert-doc.ps1'
        script_path.write_text(
            r"""
param([string]$Source, [string]$Output)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.AutomationSecurity = 3
$word.Options.SaveNormalPrompt = $false
$word.Options.ConfirmConversions = $false
$signature = @'
using System;
using System.Runtime.InteropServices;
public static class WordWindowProcess {
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
'@
Add-Type -TypeDefinition $signature
$wordProcessId = 0
[void][WordWindowProcess]::GetWindowThreadProcessId([IntPtr]$word.Hwnd, [ref]$wordProcessId)
$processIdPath = Join-Path (Split-Path -Parent $Source) 'word-process-id.txt'
$wordProcessId | Set-Content -LiteralPath $processIdPath -Encoding ascii
$doc = $null
try {
    $doc = $word.Documents.Open(
        $Source,
        $false,
        $true,
        $false,
        '',
        '',
        $false,
        '',
        '',
        0,
        0,
        $false,
        $true,
        0,
        $true
    )
    $doc.SaveAs2($Output, 16)
}
finally {
    if ($null -ne $doc) {
        $doc.Close($false)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc)
    }
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
""".strip(),
            encoding='utf-8-sig',
        )
        try:
            result = subprocess.run(
                [
                    'powershell.exe',
                    '-NoProfile',
                    '-NonInteractive',
                    '-ExecutionPolicy',
                    'Bypass',
                    '-File',
                    str(script_path.resolve()),
                    str(source_path),
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            IndicatorDocumentConverter._terminate_conversion_word_processes(
                source_path.parent / 'word-process-id.txt',
                existing_word_process_ids,
            )
            raise IndicatorParsingError('Microsoft Word превысил время обработки .doc-файла.') from exc
        except OSError as exc:
            raise IndicatorParsingError('Не удалось запустить Microsoft Word для обработки .doc.') from exc
        if result.returncode != 0:
            raise IndicatorParsingError('Microsoft Word не смог преобразовать загруженный .doc-файл.')

    @staticmethod
    def _get_word_process_ids() -> set[int]:
        if os.name != 'nt':
            return set()
        try:
            result = subprocess.run(
                [
                    'powershell.exe',
                    '-NoProfile',
                    '-NonInteractive',
                    '-Command',
                    '(Get-Process WINWORD -ErrorAction SilentlyContinue).Id',
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return set()
        return {
            int(line.strip())
            for line in result.stdout.splitlines()
            if line.strip().isdigit()
        }

    @staticmethod
    def _terminate_conversion_word_processes(
        pid_path: Path,
        existing_process_ids: set[int],
    ) -> None:
        process_ids = IndicatorDocumentConverter._get_word_process_ids() - existing_process_ids
        try:
            process_id = pid_path.read_text(encoding='ascii').strip()
        except OSError:
            process_id = ''
        if process_id.isdigit():
            process_ids.add(int(process_id))

        for process_id in process_ids:
            try:
                os.kill(process_id, signal.SIGTERM)
            except OSError:
                subprocess.run(
                    ['taskkill.exe', '/PID', str(process_id), '/T', '/F'],
                    check=False,
                    capture_output=True,
                    timeout=10,
                )
