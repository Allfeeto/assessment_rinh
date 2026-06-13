(function () {
    function parseExtraParams(raw) {
        if (!raw) {
            return new URLSearchParams();
        }
        try {
            return new URLSearchParams(raw);
        } catch (e) {
            return new URLSearchParams();
        }
    }

    function parseDynamicParams(raw) {
        if (!raw) {
            return [];
        }
        return raw.split(',')
            .map(item => item.trim())
            .filter(Boolean)
            .map(item => {
                const separatorIndex = item.indexOf(':');
                if (separatorIndex < 0) {
                    return null;
                }
                return {
                    fieldId: item.slice(0, separatorIndex).trim(),
                    paramName: item.slice(separatorIndex + 1).trim(),
                };
            })
            .filter(item => item && item.fieldId && item.paramName);
    }

    function normalizeAutocompleteLabel(value) {
        return String(value || '')
            .replace(/[\u200b-\u200d\ufeff]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function ensureOption(select, id, label) {
        const value = String(id);
        const normalizedLabel = normalizeAutocompleteLabel(label);
        let option = Array.from(select.options).find(item => item.value === value);
        if (!option) {
            option = document.createElement('option');
            option.value = value;
            option.textContent = normalizedLabel;
            select.appendChild(option);
        } else {
            option.textContent = normalizedLabel;
        }
        option.selected = true;
        select.dataset.autocompleteSelectedLabel = normalizedLabel;
        delete select.dataset.autocompleteCleared;
    }

    function setAutocompleteInputValue(input, value) {
        const normalizedValue = normalizeAutocompleteLabel(value);
        input.value = normalizedValue;
        input.title = normalizedValue;
        window.requestAnimationFrame(() => {
            input.scrollLeft = 0;
        });
    }

    function buildLookupUrl(select, query) {
        const baseUrl = select.dataset.autocompleteUrl || '/core/lookup/';
        const kind = select.dataset.autocompleteKind;
        if (!kind) {
            return null;
        }

        const params = new URLSearchParams();
        params.set('kind', kind);
        params.set('q', query || '');
        params.set('limit', '20');
        const selectedLabel = normalizeAutocompleteLabel(select.dataset.autocompleteSelectedLabel);
        if (select.value && selectedLabel && !(query || '').trim()) {
            params.set('selected_id', select.value);
        }

        const parentId = select.dataset.autocompleteParent;
        const parentParam = select.dataset.autocompleteParentParam;
        if (parentId && parentParam) {
            const parentField = document.getElementById(parentId);
            const parentValue = parentField ? parentField.value : '';
            if (parentValue) {
                params.set(parentParam, parentValue);
            } else if (select.dataset.autocompleteParentRequired === '1') {
                return null;
            }
        }

        const extraParams = parseExtraParams(select.dataset.autocompleteExtra);
        extraParams.forEach((value, key) => params.set(key, value));

        const dynamicParams = parseDynamicParams(select.dataset.autocompleteDynamicParams);
        dynamicParams.forEach(item => {
            const field = document.getElementById(item.fieldId);
            if (field && field.value) {
                params.set(item.paramName, field.value);
            }
        });

        const hasQuery = baseUrl.indexOf('?') >= 0;
        const separator = hasQuery ? '&' : '?';
        return baseUrl + separator + params.toString();
    }

    function initAutocomplete(select) {
        if (select.dataset.autocompleteReady === '1') {
            return;
        }
        if (!select.dataset.autocompleteKind) {
            return;
        }
        select.dataset.autocompleteReady = '1';
        select.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'autocomplete-shell';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'autocomplete-input';
        input.autocomplete = 'off';
        const enabledPlaceholder = select.dataset.autocompletePlaceholder || 'Начните вводить для поиска';
        const disabledPlaceholder = select.dataset.autocompleteDisabledPlaceholder || enabledPlaceholder;
        input.placeholder = enabledPlaceholder;
        if (select.id) {
            input.id = select.id + '__search';
            const label = document.querySelector('label[for="' + select.id + '"]');
            if (label) {
                label.setAttribute('for', input.id);
            }
        }

        const menu = document.createElement('div');
        menu.className = 'autocomplete-menu';

        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.value) {
            setAutocompleteInputValue(input, selectedOption.textContent || '');
            select.dataset.autocompleteSelectedLabel = normalizeAutocompleteLabel(input.value);
        }

        wrapper.appendChild(input);
        wrapper.appendChild(menu);
        select.parentNode.insertBefore(wrapper, select.nextSibling);

        let activeController = null;
        let debounceTimer = null;
        let requestSequence = 0;

        function closeMenu() {
            menu.style.display = 'none';
            menu.innerHTML = '';
        }

        function renderStatus(text) {
            menu.innerHTML = '';
            const row = document.createElement('div');
            row.className = 'autocomplete-empty';
            row.textContent = text;
            menu.appendChild(row);
            menu.style.display = 'block';
        }

        function clearSelection() {
            const hadValue = Boolean(select.value);
            if (select.value) {
                select.dataset.autocompleteCleared = '1';
            }
            select.value = '';
            delete select.dataset.autocompleteSelectedLabel;
            if (hadValue) {
                select.dispatchEvent(new Event('autocomplete-value-cleared', {bubbles: true}));
            }
        }

        function getLookupQuery() {
            const query = normalizeAutocompleteLabel(input.value);
            const selectedLabel = normalizeAutocompleteLabel(select.dataset.autocompleteSelectedLabel);
            if (select.value && selectedLabel && query === selectedLabel) {
                return '';
            }
            return query;
        }

        function setInputStateByParent() {
            const parentId = select.dataset.autocompleteParent;
            if (!parentId || select.dataset.autocompleteParentRequired !== '1') {
                input.disabled = false;
                return;
            }
            const parentField = document.getElementById(parentId);
            const hasParentValue = parentField && parentField.value;
            input.disabled = !hasParentValue;
            input.placeholder = input.disabled ? disabledPlaceholder : enabledPlaceholder;
            if (input.disabled) {
                setAutocompleteInputValue(input, '');
                clearSelection();
                closeMenu();
            }
        }

        function renderResults(results) {
            menu.innerHTML = '';
            if (!results.length) {
                const empty = document.createElement('div');
                empty.className = 'autocomplete-empty';
                empty.textContent = 'Ничего не найдено';
                menu.appendChild(empty);
                menu.style.display = 'block';
                return;
            }

            results.forEach(item => {
                const label = normalizeAutocompleteLabel(item.label);
                const row = document.createElement('div');
                row.className = 'autocomplete-item';
                row.textContent = label;
                row.dataset.id = String(item.id);
                row.dataset.label = label;
                row.addEventListener('mousedown', event => {
                    event.preventDefault();
                    ensureOption(select, item.id, label);
                    setAutocompleteInputValue(input, label);
                    closeMenu();
                    select.dispatchEvent(new Event('change', {bubbles: true}));
                });
                menu.appendChild(row);
            });
            menu.style.display = 'block';
        }

        function fetchResults(query) {
            const endpoint = buildLookupUrl(select, query);
            if (!endpoint) {
                closeMenu();
                return;
            }

            if (activeController) {
                activeController.abort();
            }
            activeController = new AbortController();
            const currentRequest = ++requestSequence;
            renderStatus('Загрузка...');

            fetch(endpoint, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                signal: activeController.signal,
            })
                .then(response => response.json())
                .then(data => {
                    if (currentRequest !== requestSequence) {
                        return;
                    }
                    renderResults(data.results || []);
                })
                .catch(error => {
                    if (error && error.name === 'AbortError') {
                        return;
                    }
                    if (currentRequest !== requestSequence) {
                        return;
                    }
                    renderStatus('Не удалось загрузить варианты');
                });
        }

        function scheduleFetch(query) {
            if (debounceTimer) {
                window.clearTimeout(debounceTimer);
            }
            debounceTimer = window.setTimeout(() => fetchResults(query), 250);
        }

        function resetAfterDependencyChange() {
            if (debounceTimer) {
                window.clearTimeout(debounceTimer);
                debounceTimer = null;
            }
            if (activeController) {
                activeController.abort();
            }
            requestSequence += 1;
            setAutocompleteInputValue(input, '');
            clearSelection();
            closeMenu();
            setInputStateByParent();
        }

        input.addEventListener('input', () => {
            const selectedLabel = normalizeAutocompleteLabel(select.dataset.autocompleteSelectedLabel);
            const query = normalizeAutocompleteLabel(input.value);
            if (select.value && query !== selectedLabel) {
                clearSelection();
            }
            scheduleFetch(query);
        });

        input.addEventListener('focus', () => {
            fetchResults(getLookupQuery());
        });

        input.addEventListener('blur', () => {
            if (!input.value.trim() && select.dataset.autocompleteCleared === '1') {
                delete select.dataset.autocompleteCleared;
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        });

        document.addEventListener('click', event => {
            if (!wrapper.contains(event.target)) {
                closeMenu();
            }
        });

        const parentId = select.dataset.autocompleteParent;
        if (parentId) {
            const parentField = document.getElementById(parentId);
            if (parentField) {
                parentField.addEventListener('change', resetAfterDependencyChange);
                parentField.addEventListener('autocomplete-value-cleared', resetAfterDependencyChange);
            }
        }
        setInputStateByParent();
    }

    function initAutoSubmitOnChange() {
        document.querySelectorAll('[data-auto-submit-change="1"]').forEach(field => {
            field.addEventListener('change', () => {
                const form = field.closest('form');
                if (!form) {
                    return;
                }
                if ((form.method || 'get').toLowerCase() !== 'get') {
                    return;
                }
                form.submit();
            });
        });
    }

    function initMobileNavigation() {
        const toggle = document.querySelector('[data-mobile-nav-toggle]');
        const menu = document.querySelector('[data-mobile-nav-menu]');
        if (!toggle || !menu) {
            return;
        }

        function setOpen(isOpen) {
            menu.classList.toggle('is-open', isOpen);
            toggle.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            toggle.setAttribute('aria-label', isOpen ? 'Закрыть меню' : 'Открыть меню');
        }

        toggle.addEventListener('click', () => {
            setOpen(toggle.getAttribute('aria-expanded') !== 'true');
        });

        menu.addEventListener('click', event => {
            if (event.target.closest('a')) {
                setOpen(false);
            }
        });

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                setOpen(false);
            }
        });

        window.addEventListener('resize', () => {
            if (window.innerWidth > 760) {
                setOpen(false);
            }
        });
    }

    initMobileNavigation();
    document.querySelectorAll('select[data-autocomplete-kind]').forEach(initAutocomplete);
    initAutoSubmitOnChange();
})();
