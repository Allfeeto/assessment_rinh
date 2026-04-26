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

    function ensureOption(select, id, label) {
        const value = String(id);
        let option = Array.from(select.options).find(item => item.value === value);
        if (!option) {
            option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            select.appendChild(option);
        } else {
            option.textContent = label;
        }
        option.selected = true;
        select.dataset.autocompleteSelectedLabel = label;
        delete select.dataset.autocompleteCleared;
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
        const selectedLabel = (select.dataset.autocompleteSelectedLabel || '').trim();
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
        input.placeholder = select.dataset.autocompletePlaceholder || 'Начните вводить для поиска';
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
            input.value = selectedOption.textContent || '';
            select.dataset.autocompleteSelectedLabel = input.value;
        }

        wrapper.appendChild(input);
        wrapper.appendChild(menu);
        select.parentNode.insertBefore(wrapper, select.nextSibling);

        let activeController = null;

        function closeMenu() {
            menu.style.display = 'none';
            menu.innerHTML = '';
        }

        function clearSelection() {
            if (select.value) {
                select.dataset.autocompleteCleared = '1';
            }
            select.value = '';
            delete select.dataset.autocompleteSelectedLabel;
        }

        function getLookupQuery() {
            const query = input.value.trim();
            const selectedLabel = (select.dataset.autocompleteSelectedLabel || '').trim();
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
            if (input.disabled) {
                input.value = '';
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
                const row = document.createElement('div');
                row.className = 'autocomplete-item';
                row.textContent = item.label;
                row.dataset.id = String(item.id);
                row.dataset.label = item.label;
                row.addEventListener('mousedown', event => {
                    event.preventDefault();
                    ensureOption(select, item.id, item.label);
                    input.value = item.label;
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

            fetch(endpoint, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                signal: activeController.signal,
            })
                .then(response => response.json())
                .then(data => renderResults(data.results || []))
                .catch(() => {
                });
        }

        input.addEventListener('input', () => {
            const selectedLabel = (select.dataset.autocompleteSelectedLabel || '').trim();
            const query = input.value.trim();
            if (select.value && query !== selectedLabel) {
                clearSelection();
            }
            fetchResults(query);
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
                parentField.addEventListener('change', () => {
                    input.value = '';
                    clearSelection();
                    closeMenu();
                    setInputStateByParent();
                });
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

    function initDependentSelects() {
        function updateOptions(parentSelect, childSelect) {
            const template = childSelect.dataset.fetchUrl;
            if (!template) {
                return;
            }

            const parentValue = parentSelect.value;
            const selectedBefore = Array.from(childSelect.options)
                .filter(option => option.selected)
                .map(option => option.value);

            if (!parentValue) {
                if (childSelect.multiple) {
                    childSelect.innerHTML = '';
                } else {
                    childSelect.innerHTML = '<option value="">---------</option>';
                }
                return;
            }

            const url = template.replace('{value}', encodeURIComponent(parentValue));
            fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
                .then(response => response.json())
                .then(data => {
                    const results = data.results || [];
                    const restored = new Set(selectedBefore);

                    if (childSelect.multiple) {
                        childSelect.innerHTML = '';
                    } else {
                        childSelect.innerHTML = '<option value="">---------</option>';
                    }

                    results.forEach(item => {
                        const option = document.createElement('option');
                        option.value = String(item.id);
                        option.textContent = item.label;
                        if (restored.has(String(item.id))) {
                            option.selected = true;
                        }
                        childSelect.appendChild(option);
                    });
                })
                .catch(() => {
                });
        }

        document.querySelectorAll('select[data-dependent-child]').forEach(parentSelect => {
            const childId = parentSelect.dataset.dependentChild;
            const childSelect = document.getElementById(childId);
            if (!childSelect) {
                return;
            }

            parentSelect.addEventListener('change', () => updateOptions(parentSelect, childSelect));
            if (parentSelect.value) {
                updateOptions(parentSelect, childSelect);
            }
        });
    }

    document.querySelectorAll('select[data-autocomplete-kind]').forEach(initAutocomplete);
    initDependentSelects();
    initAutoSubmitOnChange();
})();
