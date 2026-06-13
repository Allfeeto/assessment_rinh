(() => {
    function blockRoot(blockName) {
        return document.querySelector(`[data-compact-block="${blockName}"]`);
    }

    function requestUrl(sourceUrl, blockName) {
        const url = new URL(sourceUrl, window.location.href);
        url.searchParams.set('_fragment', blockName);
        url.hash = '';
        return url;
    }

    function visibleUrl(sourceUrl) {
        const url = new URL(sourceUrl, window.location.href);
        url.searchParams.delete('_fragment');
        return url;
    }

    async function loadBlock(blockName, sourceUrl) {
        const block = blockRoot(blockName);
        if (!block) {
            window.location.assign(sourceUrl);
            return;
        }

        const nextVisibleUrl = visibleUrl(sourceUrl);
        block.classList.add('compact-block-loading');
        block.setAttribute('aria-busy', 'true');

        try {
            const response = await fetch(requestUrl(sourceUrl, blockName), {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                credentials: 'same-origin',
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            block.innerHTML = await response.text();
            window.history.replaceState({}, '', nextVisibleUrl);
        } catch (_error) {
            window.location.assign(nextVisibleUrl);
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
        loadBlock(link.dataset.compactLink, link.href);
    });

    document.addEventListener('change', event => {
        const form = event.target.closest('form[data-compact-form]');
        if (!form) {
            return;
        }
        const url = new URL(window.location.href);
        new FormData(form).forEach((value, name) => {
            if (value === '') {
                url.searchParams.delete(name);
            } else {
                url.searchParams.set(name, value);
            }
        });
        const pageParam = form.dataset.compactPageParam;
        if (pageParam) {
            url.searchParams.delete(pageParam);
        }
        loadBlock(form.dataset.compactForm, url);
    });
})();
