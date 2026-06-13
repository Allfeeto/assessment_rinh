(() => {
    async function loadBlock(blockName, sourceUrl) {
        const block = document.querySelector(`[data-async-block="${blockName}"]`);
        if (!block) {
            window.location.assign(sourceUrl);
            return;
        }

        const url = new URL(sourceUrl, window.location.href);
        url.hash = '';
        block.classList.add('compact-block-loading');
        block.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                credentials: 'same-origin',
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const documentCopy = new DOMParser().parseFromString(await response.text(), 'text/html');
            const replacement = documentCopy.querySelector(`[data-async-block="${blockName}"]`);
            if (!replacement) {
                throw new Error('Block not found');
            }
            block.innerHTML = replacement.innerHTML;
            window.history.replaceState({}, '', url);
        } catch (_error) {
            window.location.assign(url);
        } finally {
            block.classList.remove('compact-block-loading');
            block.removeAttribute('aria-busy');
        }
    }

    document.addEventListener('click', event => {
        const link = event.target.closest('a[data-async-link]');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        loadBlock(link.dataset.asyncLink, link.href);
    });

    document.addEventListener('submit', event => {
        const form = event.target.closest('form[data-async-form]');
        if (!form || (form.method || 'get').toLowerCase() !== 'get') {
            return;
        }
        event.preventDefault();
        const url = new URL(form.action || window.location.href, window.location.href);
        url.search = new URLSearchParams(new FormData(form)).toString();
        loadBlock(form.dataset.asyncForm, url);
    });
})();
