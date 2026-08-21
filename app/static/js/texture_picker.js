(() => {
    'use strict';

    const instances = new WeakMap();
    let openedPicker = null;
    let pickerSequence = 0;

    class TexturePicker {
        constructor(select) {
            this.select = select;
            this.renderQueued = false;
            this.imageObserver = null;
            this.id = `texture-picker-${++pickerSequence}`;
            this.previewKind = select.dataset.texturePreview || '';
            this.label = this.findLabel();

            this.wrapper = document.createElement('div');
            this.wrapper.className = 'texture-picker';
            this.wrapper.dataset.previewKind = this.previewKind;
            this.wrapper.style.width = select.style.width || '100%';

            select.parentNode.insertBefore(this.wrapper, select);
            this.wrapper.appendChild(select);
            select.classList.add('texture-picker__native');
            select.tabIndex = -1;
            select.setAttribute('aria-hidden', 'true');

            this.trigger = document.createElement('button');
            this.trigger.type = 'button';
            this.trigger.id = `${this.id}-trigger`;
            this.trigger.className = 'texture-picker__trigger';
            this.trigger.setAttribute('role', 'combobox');
            this.trigger.setAttribute('aria-haspopup', 'listbox');
            this.trigger.setAttribute('aria-expanded', 'false');
            this.trigger.setAttribute('aria-controls', `${this.id}-listbox`);
            if (this.label) {
                if (!this.label.id) this.label.id = `${this.id}-label`;
                this.label.htmlFor = this.trigger.id;
                this.trigger.setAttribute(
                    'aria-labelledby',
                    `${this.label.id} ${this.id}-value`,
                );
            } else {
                this.trigger.setAttribute('aria-label', this.labelText());
            }
            this.wrapper.appendChild(this.trigger);

            this.menu = document.createElement('div');
            this.menu.id = `${this.id}-listbox`;
            this.menu.className = 'texture-picker__menu';
            this.menu.dataset.previewKind = this.previewKind;
            this.menu.setAttribute('role', 'listbox');
            if (this.label) {
                this.menu.setAttribute('aria-labelledby', this.label.id);
            } else {
                this.menu.setAttribute('aria-label', this.labelText());
            }
            document.body.appendChild(this.menu);

            this.trigger.addEventListener('click', () => this.toggle());
            this.trigger.addEventListener('keydown', (event) => this.onTriggerKeydown(event));
            this.menu.addEventListener('keydown', (event) => this.onMenuKeydown(event));
            select.addEventListener('input', () => this.sync());
            select.addEventListener('change', () => this.sync());

            this.mutationObserver = new MutationObserver(() => this.scheduleRender());
            this.mutationObserver.observe(select, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'disabled', 'label', 'selected'],
            });

            this.render();
        }

        findLabel() {
            if (this.select.id) {
                const explicit = document.querySelector(
                    `label[for="${CSS.escape(this.select.id)}"]`,
                );
                if (explicit) return explicit;
            }
            return this.select.closest('.form-row, .door3d-field')?.querySelector('label') || null;
        }

        labelText() {
            return this.label ? this.label.textContent.trim() : 'Выбор текстуры';
        }

        scheduleRender() {
            if (this.renderQueued) return;
            this.renderQueued = true;
            queueMicrotask(() => {
                this.renderQueued = false;
                this.render();
            });
        }

        previewUrl(option) {
            if (!option || !option.value) return '';
            if (option.dataset.previewUrl) return option.dataset.previewUrl;

            const endpoint = this.select.dataset.previewEndpoint;
            if (!endpoint) return '';
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('name', option.value);
            return `${url.pathname}${url.search}`;
        }

        makeThumbnail(option, lazy) {
            const thumbnail = document.createElement('span');
            thumbnail.className = 'texture-picker__thumbnail';
            thumbnail.setAttribute('aria-hidden', 'true');

            const previewUrl = this.previewUrl(option);
            if (!previewUrl) {
                thumbnail.classList.add('is-missing');
                thumbnail.title = 'Предпросмотр недоступен';
                return thumbnail;
            }

            const image = document.createElement('img');
            image.alt = '';
            image.decoding = 'async';
            image.addEventListener('load', () => thumbnail.classList.add('is-loaded'));
            image.addEventListener('error', () => {
                image.remove();
                thumbnail.classList.add('is-missing');
                thumbnail.title = 'Предпросмотр недоступен';
            });
            if (lazy) {
                image.dataset.src = previewUrl;
            } else {
                image.src = previewUrl;
            }
            thumbnail.appendChild(image);
            return thumbnail;
        }

        render() {
            const fragment = document.createDocumentFragment();
            Array.from(this.select.options).forEach((option, index) => {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'texture-picker__option';
                item.dataset.optionIndex = String(index);
                item.setAttribute('role', 'option');
                item.setAttribute('aria-selected', option.selected ? 'true' : 'false');
                item.tabIndex = -1;
                item.disabled = option.disabled;

                const name = document.createElement('span');
                name.className = 'texture-picker__option-name';
                name.textContent = option.textContent;
                item.append(name, this.makeThumbnail(option, true));
                item.addEventListener('click', () => this.choose(index));
                fragment.appendChild(item);
            });

            this.menu.replaceChildren(fragment);
            this.sync();
            if (this.isOpen()) this.startLazyLoading();
        }

        sync() {
            const option = this.select.selectedOptions[0] || this.select.options[0];
            const name = document.createElement('span');
            name.id = `${this.id}-value`;
            name.className = 'texture-picker__selected-name';
            name.textContent = option ? option.textContent : '-Выбрать-';

            const chevron = document.createElement('span');
            chevron.className = 'texture-picker__chevron';
            chevron.setAttribute('aria-hidden', 'true');

            this.trigger.replaceChildren(
                name,
                this.makeThumbnail(option, false),
                chevron,
            );
            this.trigger.disabled = this.select.disabled;
            this.trigger.classList.toggle(
                'field-error',
                this.select.classList.contains('field-error'),
            );

            Array.from(this.menu.children).forEach((item, index) => {
                const selected = Boolean(this.select.options[index]?.selected);
                item.classList.toggle('is-selected', selected);
                item.setAttribute('aria-selected', selected ? 'true' : 'false');
            });
        }

        choose(index) {
            const option = this.select.options[index];
            if (!option || option.disabled) return;
            this.select.value = option.value;
            this.select.dispatchEvent(new Event('input', {bubbles: true}));
            this.select.dispatchEvent(new Event('change', {bubbles: true}));
            this.sync();
            this.close();
            this.trigger.focus();
        }

        isOpen() {
            return this.menu.classList.contains('is-open');
        }

        toggle() {
            if (this.isOpen()) {
                this.close();
            } else {
                this.open();
            }
        }

        open() {
            if (this.trigger.disabled) return;
            if (openedPicker && openedPicker !== this) openedPicker.close();
            openedPicker = this;
            this.menu.classList.add('is-open');
            this.trigger.classList.add('is-open');
            this.trigger.setAttribute('aria-expanded', 'true');
            this.positionMenu();
            this.startLazyLoading();
        }

        close() {
            if (!this.isOpen()) return;
            this.menu.classList.remove('is-open');
            this.trigger.classList.remove('is-open');
            this.trigger.setAttribute('aria-expanded', 'false');
            if (this.imageObserver) this.imageObserver.disconnect();
            if (openedPicker === this) openedPicker = null;
        }

        positionMenu() {
            const rect = this.trigger.getBoundingClientRect();
            const viewportMargin = 8;
            const width = Math.min(
                Math.max(rect.width, 340),
                window.innerWidth - viewportMargin * 2,
            );
            const left = Math.min(
                Math.max(viewportMargin, rect.left),
                window.innerWidth - width - viewportMargin,
            );
            const spaceBelow = window.innerHeight - rect.bottom - viewportMargin;
            const spaceAbove = rect.top - viewportMargin;
            const maxHeight = Math.max(120, Math.min(360, Math.max(spaceBelow, spaceAbove) - 4));

            this.menu.style.left = `${left}px`;
            this.menu.style.width = `${width}px`;
            this.menu.style.maxHeight = `${maxHeight}px`;

            if (spaceBelow >= 180 || spaceBelow >= spaceAbove) {
                this.menu.style.top = `${rect.bottom + 4}px`;
            } else {
                const menuHeight = Math.min(this.menu.scrollHeight, maxHeight);
                this.menu.style.top = `${Math.max(
                    viewportMargin,
                    rect.top - menuHeight - 4,
                )}px`;
            }
        }

        startLazyLoading() {
            if (this.imageObserver) this.imageObserver.disconnect();
            const images = this.menu.querySelectorAll('img[data-src]');
            if (!('IntersectionObserver' in window)) {
                images.forEach((image) => {
                    image.src = image.dataset.src;
                    delete image.dataset.src;
                });
                return;
            }

            this.imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    const image = entry.target;
                    image.src = image.dataset.src;
                    delete image.dataset.src;
                    observer.unobserve(image);
                });
            }, {
                root: this.menu,
                rootMargin: '120px 0px',
            });
            images.forEach((image) => this.imageObserver.observe(image));
        }

        focusOption(offset) {
            const options = Array.from(
                this.menu.querySelectorAll('.texture-picker__option:not(:disabled)'),
            );
            if (!options.length) return;
            const activeIndex = options.indexOf(document.activeElement);
            const selectedIndex = options.findIndex((item) => item.classList.contains('is-selected'));
            const startIndex = activeIndex >= 0 ? activeIndex : Math.max(selectedIndex, 0);
            const nextIndex = (startIndex + offset + options.length) % options.length;
            options[nextIndex].focus();
            options[nextIndex].scrollIntoView({block: 'nearest'});
        }

        focusAdjacentControl(backwards) {
            const controls = Array.from(document.querySelectorAll(
                'a[href], button, input, select, textarea, [tabindex]',
            )).filter((element) => (
                element.tabIndex >= 0
                && !element.disabled
                && !this.menu.contains(element)
                && element.getClientRects().length > 0
            ));
            const currentIndex = controls.indexOf(this.trigger);
            const nextIndex = currentIndex + (backwards ? -1 : 1);
            const nextControl = controls[nextIndex];
            if (nextControl) nextControl.focus();
            else this.trigger.focus();
        }

        onTriggerKeydown(event) {
            if (event.key === 'Tab') {
                this.close();
                return;
            }
            if (event.key === 'Escape' && this.isOpen()) {
                event.preventDefault();
                this.close();
                return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) return;
            event.preventDefault();
            if (!this.isOpen()) this.open();
            if (event.key === 'ArrowUp') {
                this.focusOption(-1);
            } else {
                this.focusOption(0);
            }
        }

        onMenuKeydown(event) {
            if (event.key === 'Tab') {
                event.preventDefault();
                this.close();
                this.focusAdjacentControl(event.shiftKey);
            } else if (event.key === 'Escape') {
                event.preventDefault();
                this.close();
                this.trigger.focus();
            } else if (event.key === 'ArrowDown') {
                event.preventDefault();
                this.focusOption(1);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                this.focusOption(-1);
            } else if (event.key === 'Home' || event.key === 'End') {
                event.preventDefault();
                const options = this.menu.querySelectorAll(
                    '.texture-picker__option:not(:disabled)',
                );
                const target = event.key === 'Home' ? options[0] : options[options.length - 1];
                if (target) target.focus();
            }
        }
    }

    function initialiseTexturePickers() {
        document.querySelectorAll('select[data-texture-preview]').forEach((select) => {
            if (instances.has(select)) return;
            instances.set(select, new TexturePicker(select));
        });
    }

    document.addEventListener('pointerdown', (event) => {
        if (!openedPicker) return;
        if (
            openedPicker.wrapper.contains(event.target)
            || openedPicker.menu.contains(event.target)
        ) return;
        openedPicker.close();
    });

    document.addEventListener('focusin', (event) => {
        if (!openedPicker) return;
        if (
            openedPicker.wrapper.contains(event.target)
            || openedPicker.menu.contains(event.target)
        ) return;
        openedPicker.close();
    });

    window.addEventListener('resize', () => openedPicker?.positionMenu());
    window.addEventListener('scroll', () => openedPicker?.positionMenu(), true);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialiseTexturePickers);
    } else {
        initialiseTexturePickers();
    }
})();
