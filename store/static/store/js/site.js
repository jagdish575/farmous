document.addEventListener('DOMContentLoaded', () => {
    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    };

    const csrfToken = getCookie('csrftoken');

    /* ── Toast notifications ── */
    const showToast = (message, type = 'success') => {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
        const toast = document.createElement('div');
        toast.className = `toast-message ${type}`;
        toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);
        window.setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(1rem)';
            toast.style.transition = '0.3s ease';
            window.setTimeout(() => toast.remove(), 300);
        }, 3200);
    };

    /* ── Cart drawer ── */
    const drawer = document.getElementById('cartDrawer');
    const drawerOpen = document.getElementById('drawerCartOpen');
    const drawerClose = document.getElementById('drawerClose');
    const drawerBackdrop = document.getElementById('drawerBackdrop');
    const isAuthenticated = document.body.dataset.auth === '1';
    const defaultImage = 'https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=200&q=80';

    const openDrawer = () => {
        drawer?.classList.add('open');
        document.body.classList.add('drawer-open');
    };
    const closeDrawer = () => {
        drawer?.classList.remove('open');
        document.body.classList.remove('drawer-open');
    };

    drawerOpen?.addEventListener('click', () => {
        openDrawer();
        if (isAuthenticated) refreshDrawer();
    });
    drawerClose?.addEventListener('click', closeDrawer);
    drawerBackdrop?.addEventListener('click', closeDrawer);

    /* ── Mobile nav active state ── */
    const currentPath = window.location.pathname;
    document.querySelectorAll('.mobile-bottom-nav .nav-link').forEach((link) => {
        const href = link.getAttribute('href');
        if (!href) return;
        if (href === '/' && currentPath === '/') {
            link.classList.add('active');
        } else if (href !== '/' && currentPath.startsWith(href)) {
            link.classList.add('active');
        }
    });

    /* ── Search ── */
    const searchConfigs = [
        { input: document.getElementById('searchInput'), dropdown: document.getElementById('searchDropdown') },
        { input: document.getElementById('mobileSearchInput'), dropdown: document.getElementById('mobileSearchDropdown') },
    ];

    const activeSearchState = new WeakMap();

    const getSearchState = (input) => {
        if (!activeSearchState.has(input)) {
            activeSearchState.set(input, { activeIndex: -1, results: [], query: '' });
        }
        return activeSearchState.get(input);
    };

    const renderSearchResults = (data, dropdown, input) => {
        if (!dropdown) return;
        const results = data.results || [];
        const total = data.total || results.length;
        const query = input.value.trim();
        const state = getSearchState(input);
        state.results = results;
        state.query = query;
        state.activeIndex = -1;

        dropdown.innerHTML = '';

        if (!query) {
            dropdown.classList.add('d-none');
            return;
        }

        if (data.loading) {
            const loading = document.createElement('div');
            loading.className = 'loading';
            loading.textContent = 'Searching';
            dropdown.appendChild(loading);
            dropdown.classList.remove('d-none');
            return;
        }

        if (!results.length) {
            const empty = document.createElement('div');
            empty.className = 'empty';
            empty.innerHTML = `<i class="fas fa-search mb-2 d-block" style="font-size:1.5rem;opacity:0.3"></i>No medicines found for "<strong>${query}</strong>"`;
            dropdown.appendChild(empty);
            dropdown.classList.remove('d-none');
            return;
        }

        const header = document.createElement('div');
        header.className = 'search-dropdown-header';
        header.textContent = 'Suggestions';
        dropdown.appendChild(header);

        results.forEach((item, index) => {
            const el = document.createElement('a');
            el.href = item.url;
            el.className = 'search-dropdown-item';
            el.dataset.index = index;
            const stockLabel = item.in_stock ? 'In stock' : 'Out of stock';
            const stockClass = item.in_stock ? 'text-success' : 'text-danger';
            el.innerHTML = `
                <div class="search-thumb" style="background-image:url('${item.image || defaultImage}')"></div>
                <div class="search-info">
                    <div class="search-name">${item.name}</div>
                    <div class="search-meta">${item.category}${item.manufacturer ? ' · ' + item.manufacturer : ''} · <span class="${stockClass}">${stockLabel}</span></div>
                </div>
                <div class="search-price">₹${item.price}</div>
            `;
            el.addEventListener('mouseenter', () => setActiveItem(input, dropdown, index));
            dropdown.appendChild(el);
        });

        const footer = document.createElement('div');
        footer.className = 'search-dropdown-footer';
        footer.innerHTML = `<a href="/search/?q=${encodeURIComponent(query)}">View all ${total} result${total !== 1 ? 's' : ''} <i class="fas fa-arrow-right"></i></a>`;
        dropdown.appendChild(footer);

        dropdown.classList.remove('d-none');
    };

    const setActiveItem = (input, dropdown, index) => {
        const state = getSearchState(input);
        state.activeIndex = index;
        dropdown.querySelectorAll('.search-dropdown-item').forEach((el, i) => {
            el.classList.toggle('active', i === index);
        });
    };

    const hideAllDropdowns = (event) => {
        searchConfigs.forEach(({ input, dropdown }) => {
            if (!input || !dropdown) return;
            if (input.contains(event.target) || dropdown.contains(event.target)) return;
            dropdown.classList.add('d-none');
        });
    };

    const debounceMap = new Map();

    const fetchSearch = (input, dropdown) => {
        const query = input.value.trim();
        if (!query) {
            dropdown.classList.add('d-none');
            return;
        }

        renderSearchResults({ loading: true }, dropdown, input);

        if (debounceMap.has(input)) {
            window.clearTimeout(debounceMap.get(input));
        }

        const timeoutId = window.setTimeout(async () => {
            try {
                const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
                if (!response.ok) return;
                const data = await response.json();
                renderSearchResults(data, dropdown, input);
            } catch {
                dropdown.classList.add('d-none');
            }
        }, 200);

        debounceMap.set(input, timeoutId);
    };

    const handleSearchButton = (input) => {
        if (!input) return;
        const query = input.value.trim();
        if (!query) {
            input.focus();
            return;
        }
        saveRecentSearch(query);
        window.location.href = `/search/?q=${encodeURIComponent(query)}`;
    };

    const saveRecentSearch = (query) => {
        try {
            let recent = JSON.parse(localStorage.getItem('farmos_recent_searches') || '[]');
            recent = [query, ...recent.filter((q) => q !== query)].slice(0, 5);
            localStorage.setItem('farmos_recent_searches', JSON.stringify(recent));
        } catch { /* ignore */ }
    };

    searchConfigs.forEach(({ input, dropdown }) => {
        if (!input || !dropdown) return;

        input.addEventListener('input', () => fetchSearch(input, dropdown));

        input.addEventListener('focus', () => {
            if (dropdown.querySelector('.search-dropdown-item, .empty, .loading')) {
                dropdown.classList.remove('d-none');
            }
        });

        input.addEventListener('keydown', (event) => {
            const state = getSearchState(input);
            const items = dropdown.querySelectorAll('.search-dropdown-item');

            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (dropdown.classList.contains('d-none')) fetchSearch(input, dropdown);
                const next = Math.min(state.activeIndex + 1, items.length - 1);
                setActiveItem(input, dropdown, next);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                const prev = Math.max(state.activeIndex - 1, 0);
                setActiveItem(input, dropdown, prev);
            } else if (event.key === 'Enter') {
                if (state.activeIndex >= 0 && items[state.activeIndex]) {
                    event.preventDefault();
                    saveRecentSearch(state.query);
                    window.location.href = items[state.activeIndex].href;
                } else {
                    event.preventDefault();
                    handleSearchButton(input);
                }
            } else if (event.key === 'Escape') {
                dropdown.classList.add('d-none');
            }
        });

        const button = input.closest('.search-input-group')?.querySelector('button[data-search-submit]');
        if (button) {
            button.type = 'button';
            button.addEventListener('click', () => handleSearchButton(input));
        }
    });

    document.addEventListener('click', hideAllDropdowns);

    /* ── Cart helpers ── */
    const drawerEmptyHtml = `
        <div class="drawer-empty" id="drawerEmpty">
            <i class="fas fa-shopping-basket"></i>
            <p>Your cart is empty.<br>Add medicines to get started.</p>
            <a href="/search/" class="btn btn-primary btn-sm rounded-pill">Browse medicines</a>
        </div>`;

    const buildDrawerItemHtml = (item) => `
        <div class="drawer-item" data-item-id="${item.id}" data-unit-price="${item.price}">
            <div class="drawer-item-image" style="background-image:url('${item.image || defaultImage}')"></div>
            <div class="drawer-item-details">
                <h6>${item.medicine_name}</h6>
                <p class="text-muted small mb-1">${item.category}</p>
                <p class="small fw-semibold mb-2">₹<span class="item-total">${item.item_total.toFixed(2)}</span>
                    <span class="text-muted fw-normal">(₹<span class="item-unit-price">${item.price.toFixed(2)}</span> × <span class="quantity-value">${item.quantity}</span>)</span>
                </p>
                <div class="quantity-control">
                    <button class="quantity-btn" data-action="decrement" aria-label="Decrease">−</button>
                    <span class="quantity-value">${item.quantity}</span>
                    <button class="quantity-btn" data-action="increment" aria-label="Increase">+</button>
                </div>
            </div>
            <button class="btn btn-link drawer-remove p-0" data-item-id="${item.id}">Remove</button>
        </div>`;

    const updateCartDisplay = (count, total) => {
        document.querySelectorAll('.counter, .bottom-badge').forEach((badge) => {
            badge.textContent = count;
            badge.style.display = count > 0 ? '' : 'none';
        });
        const drawerCount = document.getElementById('drawerItemCount');
        if (drawerCount) {
            drawerCount.textContent = `${count} item${count !== 1 ? 's' : ''}`;
        }
        const drawerTotal = document.querySelector('.drawer-total-amount');
        if (drawerTotal && total !== undefined) {
            drawerTotal.textContent = `₹${total.toFixed(2)}`;
        }
        document.querySelectorAll('.summary-items-count').forEach((el) => {
            el.textContent = count;
        });
        document.querySelectorAll('.summary-total-amount').forEach((el) => {
            el.textContent = `₹${total.toFixed(2)}`;
        });
    };

    const showDrawerEmpty = () => {
        const drawerBody = document.getElementById('drawerBody');
        const drawerFooter = document.getElementById('drawerFooter');
        if (drawerBody) {
            drawerBody.innerHTML = drawerEmptyHtml;
        }
        if (drawerFooter) {
            drawerFooter.style.display = 'none';
        }
    };

    const renderDrawerItems = (data) => {
        const drawerBody = document.getElementById('drawerBody');
        const drawerFooter = document.getElementById('drawerFooter');
        if (!drawerBody || !data) return;

        updateCartDisplay(data.cart_count, data.cart_total);

        if (!data.items || !data.items.length) {
            showDrawerEmpty();
            return;
        }

        drawerBody.innerHTML = data.items.map(buildDrawerItemHtml).join('');
        if (drawerFooter) {
            drawerFooter.style.display = '';
        }
    };

    const refreshDrawer = async () => {
        if (!isAuthenticated) return;
        try {
            const response = await fetch('/api/cart/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) return;
            const data = await response.json();
            renderDrawerItems(data);
        } catch { /* ignore */ }
    };

    const postJson = async (url, data) => {
        const body = new URLSearchParams(data);
        return fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken || '',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: body.toString(),
        });
    };

    const removeCartItemElements = (itemId) => {
        document.querySelectorAll(`[data-item-id='${itemId}']`).forEach((el) => el.remove());

        const drawerBody = document.getElementById('drawerBody');
        if (drawerBody && !drawerBody.querySelector('[data-item-id]')) {
            showDrawerEmpty();
        }

        const list = document.querySelector('.cart-items-list');
        if (list && !list.querySelector('[data-item-id]')) {
            const section = list.closest('.container');
            if (section) {
                section.innerHTML = `
                    <div class="mb-4">
                        <h2 class="fw-bold">Your cart</h2>
                        <p class="text-muted mb-0">Update quantities instantly and place your order via WhatsApp.</p>
                    </div>
                    <div class="empty-state">
                        <i class="fas fa-shopping-cart"></i>
                        <h4>Your cart is empty</h4>
                        <p class="text-muted">Browse medicines and add them to your cart.</p>
                        <a href="/search/" class="btn btn-primary rounded-pill mt-2">Browse medicines</a>
                    </div>`;
            }
        }
    };

    const updateItemElements = (itemId, quantity, itemTotal) => {
        document.querySelectorAll(`[data-item-id='${itemId}']`).forEach((card) => {
            card.querySelectorAll('.quantity-value').forEach((el) => {
                el.textContent = quantity;
            });
            const totalSpan = card.querySelector('.item-total');
            if (totalSpan && itemTotal !== undefined) {
                totalSpan.textContent = itemTotal.toFixed(2);
            }
        });
    };

    const updateItemQuantity = async (itemId, quantity) => {
        const response = await postJson(`/cart/update/${itemId}/`, { quantity });
        if (!response.ok) return;
        const data = await response.json();
        updateItemElements(itemId, quantity, data.item_total);
        renderDrawerItems(data);
    };

    const removeItem = async (itemId) => {
        const response = await postJson(`/cart/remove/${itemId}/`, {});
        if (!response.ok) return;
        const data = await response.json();
        removeCartItemElements(itemId);
        renderDrawerItems(data);
        showToast('Item removed from cart', 'info');
    };

    /* ── Quick add to cart ── */
    document.body.addEventListener('click', async (event) => {
        const quickAdd = event.target.closest('.quick-add-btn');
        if (quickAdd) {
            event.preventDefault();
            const medicineId = quickAdd.dataset.medicineId;
            const medicineName = quickAdd.dataset.medicineName || 'Medicine';
            if (!medicineId) return;

            quickAdd.classList.add('loading');
            quickAdd.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            try {
                const response = await postJson(`/cart/add/${medicineId}/`, { quantity: 1 });
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                    window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                    return;
                }
                if (!response.ok) throw new Error('Failed');
                const data = await response.json();
                renderDrawerItems(data);
                showToast(`${medicineName} added to cart`, 'success');
                openDrawer();
                quickAdd.innerHTML = '<i class="fas fa-check"></i>';
                window.setTimeout(() => {
                    quickAdd.classList.remove('loading');
                    quickAdd.innerHTML = '<i class="fas fa-cart-plus"></i><span>Add</span>';
                }, 1500);
            } catch {
                showToast('Could not add to cart. Please try again.', 'error');
                quickAdd.classList.remove('loading');
                quickAdd.innerHTML = '<i class="fas fa-cart-plus"></i><span>Add</span>';
            }
            return;
        }

        const qtyButton = event.target.closest('.quantity-btn');
        const removeButton = event.target.closest('.remove-item, .drawer-remove');
        if (qtyButton) {
            const card = qtyButton.closest('[data-item-id]');
            const itemId = card?.dataset.itemId;
            const quantityValue = card?.querySelector('.quantity-value');
            if (!itemId || !quantityValue) return;
            let quantity = parseInt(quantityValue.textContent, 10) || 1;
            const action = qtyButton.dataset.action;
            if (action === 'increment') quantity += 1;
            else if (action === 'decrement') quantity -= 1;
            if (quantity < 1) removeItem(itemId);
            else updateItemQuantity(itemId, quantity);
        }
        if (removeButton) {
            event.preventDefault();
            const itemId = removeButton.dataset.itemId;
            if (!itemId) return;
            removeItem(itemId);
        }
    });

    /* ── Quantity stepper on product detail ── */
    document.querySelectorAll('.quantity-step').forEach((btn) => {
        btn.addEventListener('click', () => {
            const input = btn.closest('.quantity-selector')?.querySelector('.quantity-input');
            if (!input) return;
            const min = parseInt(input.min, 10) || 1;
            const max = parseInt(input.max, 10) || 999;
            let val = parseInt(input.value, 10) || 1;
            if (btn.dataset.action === 'increment') val = Math.min(val + 1, max);
            else val = Math.max(val - 1, min);
            input.value = val;
        });
    });
});
