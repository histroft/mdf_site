(function () {
    const MOBILE_BREAKPOINT = 768;
    let animationFrame = null;

    function fitDashboard() {
        const shell = document.querySelector('.dashboard-scale-shell');
        const dashboard = document.querySelector('.main-window');
        if (!shell || !dashboard) return;

        if (window.innerWidth <= MOBILE_BREAKPOINT) {
            dashboard.style.removeProperty('transform');
            shell.style.removeProperty('width');
            shell.style.removeProperty('height');
            return;
        }

        const bodyStyle = window.getComputedStyle(document.body);
        const horizontalPadding = parseFloat(bodyStyle.paddingLeft) + parseFloat(bodyStyle.paddingRight);
        const verticalPadding = parseFloat(bodyStyle.paddingTop) + parseFloat(bodyStyle.paddingBottom);
        const availableWidth = Math.max(1, window.innerWidth - horizontalPadding);
        const availableHeight = Math.max(1, window.innerHeight - verticalPadding);
        const baseWidth = dashboard.offsetWidth;
        const baseHeight = dashboard.offsetHeight;
        const scale = Math.min(1, availableWidth / baseWidth, availableHeight / baseHeight);

        dashboard.style.transform = `scale(${scale})`;
        shell.style.width = `${Math.floor(baseWidth * scale)}px`;
        shell.style.height = `${Math.floor(baseHeight * scale)}px`;
    }

    function scheduleFit() {
        if (animationFrame !== null) cancelAnimationFrame(animationFrame);
        animationFrame = requestAnimationFrame(() => {
            animationFrame = null;
            fitDashboard();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleFit, {once: true});
    } else {
        scheduleFit();
    }
    window.addEventListener('resize', scheduleFit);
    if (window.visualViewport) window.visualViewport.addEventListener('resize', scheduleFit);
})();
