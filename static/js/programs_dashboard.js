(() => {
    const blockParamNames = {
        directions: ['directions_expanded', 'directions_page'],
        profiles: ['profiles_expanded', 'profiles_page'],
        programs: ['programs_expanded', 'programs_page', 'programs_per_page'],
        indicator_imports: ['indicator_imports_expanded', 'indicator_imports_page'],
    };

    function mergedBlockUrl(blockName, sourceUrl) {
        const result = new URL(window.location.href);
        const source = new URL(sourceUrl, window.location.href);
        const names = blockParamNames[blockName] || [];

        names.forEach(name => {
            result.searchParams.delete(name);
            source.searchParams.getAll(name).forEach(value => result.searchParams.append(name, value));
        });
        result.hash = '';
        return result;
    }

    async function loadBlock(blockName, url) {
        const block = document.querySelector(`[data-compact-block="${blockName}"]`);
        if (!block) {
            window.location.assign(url);
            return;
        }

        const requestUrl = new URL(url);
        requestUrl.searchParams.set('_fragment', blockName);
        block.classList.add('compact-block-loading');
        block.setAttribute('aria-busy', 'true');

        try {
            const response = await fetch(requestUrl, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                credentials: 'same-origin',
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            block.innerHTML = await response.text();
            window.history.replaceState({}, '', url);
        } catch (_error) {
            window.location.assign(url);
        } finally {
            block.classList.remove('compact-block-loading');
            block.removeAttribute('aria-busy');
        }
    }

    document.addEventListener('click', event => {
        const link = event.target.closest('a[data-compact-link]');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        const blockName = link.dataset.compactLink;
        loadBlock(blockName, mergedBlockUrl(blockName, link.href));
    });

    document.addEventListener('change', event => {
        const form = event.target.closest('form[data-compact-form]');
        if (!form) {
            return;
        }
        const blockName = form.dataset.compactForm;
        const url = new URL(window.location.href);
        url.searchParams.set('programs_expanded', '1');
        url.searchParams.set('programs_per_page', form.elements.programs_per_page.value);
        url.searchParams.delete('programs_page');
        loadBlock(blockName, url);
    });
})();
