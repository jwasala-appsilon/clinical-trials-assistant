if (window.location.pathname === '/login') {
    const emailObserver = new MutationObserver((_, obs) => {
        const email = document.querySelector('input#email');
        if (email) {
            email.value = 'admin';
            email.setAttribute('value', 'admin');
            obs.disconnect();
        }
    });


    const passwordObserver = new MutationObserver((_, obs) => {
        const password = document.querySelector('input#password');
        if (password) {
            password.value = 'admin';
            password.setAttribute('value', 'admin');
            obs.disconnect();
        }
    });

    emailObserver.observe(document.documentElement, { childList: true, subtree: true });
    passwordObserver.observe(document.documentElement, { childList: true, subtree: true });
}
