import { useState, useEffect } from 'react';

export function useDarkMode() {
    const [isDark, setIsDark] = useState(() => {
        try {
            const item = window.localStorage.getItem('truedegree_theme');
            return item ? item === 'dark' : true;
        } catch (error) {
            return true;
        }
    });

    useEffect(() => {
        try {
            window.localStorage.setItem('truedegree_theme', isDark ? 'dark' : 'light');
            if (isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        } catch (error) {
            console.error('Failed to set theme setting', error);
        }
    }, [isDark]);

    const toggleDark = () => setIsDark(!isDark);

    return { isDark, toggleDark };
}
