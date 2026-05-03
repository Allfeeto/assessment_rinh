class WordExportError(ValueError):
    status_code = 400


class WordExportNotFoundError(WordExportError):
    status_code = 404
