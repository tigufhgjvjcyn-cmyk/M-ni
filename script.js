// Mobile Menu Toggle
document.addEventListener('DOMContentLoaded', function () {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    if (!hamburger || !navMenu) return;

    hamburger.addEventListener('click', function () {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
    });

    // Close menu when clicking on a link
    document.querySelectorAll('.nav-menu a').forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function (event) {
        const isClickInsideNav = navMenu.contains(event.target);
        const isClickOnHamburger = hamburger.contains(event.target);

        if (!isClickInsideNav && !isClickOnHamburger && navMenu.classList.contains('active')) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        }
    });
});

// Google Sheets Direct Link Handler
const SHEET_ID = '1PbBg84r6M3We8n5gGpJkPMCPatPe9L9JJNn8NTfmxWA';

// Function to get direct download link from Google Sheets
async function getDirectLink(cellRange) {
    try {
        // Method 1: Fetch from published Google Sheets using CSV export
        const csvUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&range=${cellRange}&gid=0`;

        const response = await fetch(csvUrl, {
            method: 'GET',
            mode: 'cors'
        });

        if (response.ok) {
            const csvData = await response.text();
            let link = csvData.trim().replace(/"/g, '').replace(/\r?\n/g, '');

            // Clean up the link and validate safety
            if (link && (link.startsWith('http://') || link.startsWith('https://'))) {
                // Check if it's a trusted domain (Google Drive, major file hosts)
                if (isTrustedDomain(link)) {
                    console.log(`Found trusted link in ${cellRange}:`, link);
                    return {
                        url: link,
                        isTrusted: true,
                        type: 'direct'
                    };
                } else {
                    console.warn(`Untrusted domain detected in ${cellRange}:`, link);
                    return {
                        url: link,
                        isTrusted: false,
                        type: 'untrusted'
                    };
                }
            }
        }

        // Method 2: Try alternative CSV format
        const altCsvUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&range=${cellRange}&gid=0`;

        const altResponse = await fetch(altCsvUrl);
        if (altResponse.ok) {
            const altCsvData = await altResponse.text();
            let altLink = altCsvData.trim().replace(/"/g, '').replace(/\r?\n/g, '');

            if (altLink && (altLink.startsWith('http://') || altLink.startsWith('https://'))) {
                if (isTrustedDomain(altLink)) {
                    return {
                        url: altLink,
                        isTrusted: true,
                        type: 'direct'
                    };
                } else {
                    return {
                        url: altLink,
                        isTrusted: false,
                        type: 'untrusted'
                    };
                }
            }
        }

        throw new Error('No valid link found');

    } catch (error) {
        console.error('Error fetching link from sheet:', error);

        // Final fallback: Open the specific cell in Google Sheets (always safe)
        const fallbackUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=0&range=${cellRange}`;
        return {
            url: fallbackUrl,
            isTrusted: true,
            type: 'sheet'
        };
    }
}

// Check if domain is trusted (to avoid Google flagging)
function isTrustedDomain(url) {
    const trustedDomains = [
        'drive.google.com',
        'docs.google.com',
        'dropbox.com',
        'mega.nz',
        'mediafire.com',
        'github.com',
        'githubusercontent.com',
        'onedrive.live.com',
        'sharepoint.com',
        'box.com',
        'wetransfer.com',
        'sendspace.com',
        'mediafire.com',
        'terabox.com'
    ];

    try {
        const domain = new URL(url).hostname.toLowerCase();
        return trustedDomains.some(trusted =>
            domain === trusted || domain.endsWith('.' + trusted)
        );
    } catch {
        return false;
    }
}

// Handle download button clicks
function handleDownload(cellRange, productName) {
    return async function (event) {
        event.preventDefault();

        const button = event.currentTarget;
        const originalText = button.innerHTML;

        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang kiểm tra...';
        button.style.pointerEvents = 'none';

        try {
            console.log(`Fetching download link for ${productName} from cell ${cellRange}...`);
            const linkData = await getDirectLink(cellRange);

            // Handle different types of links with safety warnings
            if (linkData.type === 'sheet') {
                // Safe fallback to Google Sheets
                button.innerHTML = '<i class="fas fa-external-link-alt"></i> Mở Sheet...';
                setTimeout(() => {
                    window.open(linkData.url, '_blank', 'noopener,noreferrer');
                }, 500);

            } else if (linkData.type === 'direct' && linkData.isTrusted) {
                // Trusted download link
                button.innerHTML = '<i class="fas fa-download"></i> Tải xuống an toàn...';
                setTimeout(() => {
                    // For Google Drive links, convert to direct download format
                    let finalUrl = linkData.url;
                    if (linkData.url.includes('drive.google.com/file/d/')) {
                        const fileId = linkData.url.match(/\/d\/([a-zA-Z0-9-_]+)/);
                        if (fileId) {
                            finalUrl = `https://drive.google.com/uc?export=download&id=${fileId[1]}`;
                        }
                    }
                    window.open(finalUrl, '_blank', 'noopener,noreferrer');
                }, 500);

            } else if (linkData.type === 'untrusted') {
                // Untrusted link - show warning and get user consent
                button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Cần xác nhận...';

                setTimeout(() => {
                    const userConfirm = confirm(
                        `⚠️ CẢNH BÁO BẢO MẬT\n\n` +
                        `Link tải xuống "${productName}" đến từ domain không được xác minh.\n\n` +
                        `Domain: ${new URL(linkData.url).hostname}\n\n` +
                        `Để đảm bảo an toàn:\n` +
                        `• Chỉ tải nếu bạn tin tưởng nguồn này\n` +
                        `• Quét virus sau khi tải\n` +
                        `• Hoặc chọn "Hủy" để mở Google Sheets thay thế\n\n` +
                        `Bạn có muốn tiếp tục tải xuống?`
                    );

                    if (userConfirm) {
                        window.open(linkData.url, '_blank', 'noopener,noreferrer');
                    } else {
                        // User declined, open sheet instead
                        const sheetUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=0&range=${cellRange}`;
                        window.open(sheetUrl, '_blank', 'noopener,noreferrer');
                    }
                }, 500);

            } else {
                throw new Error('Invalid link type');
            }

        } catch (error) {
            console.error('Download error:', error);

            // Show user-friendly error message
            button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Lỗi';

            setTimeout(() => {
                alert(
                    `❌ Không thể tải ${productName}\n\n` +
                    `Sẽ chuyển hướng đến Google Sheets để bạn có thể:\n` +
                    `• Xem thông tin chi tiết\n` +
                    `• Tải xuống thủ công (an toàn hơn)\n` +
                    `• Liên hệ hỗ trợ nếu cần`
                );

                // Fallback to sheet
                const fallbackUrl = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=0&range=${cellRange}`;
                window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
            }, 500);

        } finally {
            // Restore button state after delay
            setTimeout(() => {
                button.innerHTML = originalText;
                button.style.pointerEvents = 'auto';
            }, 2500);
        }
    };
}

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function (entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe elements for animation + add generic .reveal elements
document.addEventListener('DOMContentLoaded', function () {
    const animateElements = document.querySelectorAll('.feature-card, .product-card, .service-item');
    animateElements.forEach(el => {
        el.classList.add('reveal');
    });

    const revealEls = document.querySelectorAll('.reveal');
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealEls.forEach(el => revealObserver.observe(el));
});

// Active nav link on scroll
document.addEventListener('DOMContentLoaded', function () {
    const sections = Array.from(document.querySelectorAll('section[id]'));
    const links = Array.from(document.querySelectorAll('[data-nav-link]'));

    function setActiveLink() {
        const scrollPos = window.scrollY + 100; // offset for navbar
        let currentId = sections[0]?.id;
        for (const sec of sections) {
            if (scrollPos >= sec.offsetTop && scrollPos < sec.offsetTop + sec.offsetHeight) {
                currentId = sec.id;
                break;
            }
        }
        links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${currentId}`));
    }

    setActiveLink();
    window.addEventListener('scroll', () => requestAnimationFrame(setActiveLink));
});

// Counter animation for stats
function animateCounter(element, start, end, duration, suffix = '') {
    let startTimestamp = null;
    const isDecimal = end.toString().includes('.');

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);

        // Smooth easing function
        const easeProgress = 1 - Math.pow(1 - progress, 3);

        let current;
        if (isDecimal) {
            current = (easeProgress * (end - start) + start).toFixed(1);
        } else {
            current = Math.floor(easeProgress * (end - start) + start);
        }

        element.innerHTML = current + suffix;

        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Stats counter animation with improved parsing
const statsObserver = new IntersectionObserver(function (entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const statNumbers = entry.target.querySelectorAll('.stat-number');
            statNumbers.forEach(stat => {
                const text = stat.textContent.trim();
                let endValue, suffix = '';

                // Parse different formats
                if (text.includes('+')) {
                    endValue = parseInt(text.replace(/\D/g, ''));
                    suffix = '+';
                } else if (text.includes('%')) {
                    endValue = parseFloat(text.replace(/[^\d.]/g, ''));
                    suffix = '%';
                } else {
                    endValue = parseFloat(text.replace(/[^\d.]/g, ''));
                }

                // Add staggered animation delay for visual appeal
                const delay = Array.from(statNumbers).indexOf(stat) * 200;

                setTimeout(() => {
                    animateCounter(stat, 0, endValue, 2500, suffix);
                }, delay);
            });
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.3 });

document.addEventListener('DOMContentLoaded', function () {
    const statsSection = document.querySelector('.stats');
    if (statsSection) {
        statsObserver.observe(statsSection);
    }
});

// Parallax effect for hero section (lighter)
window.addEventListener('scroll', function () {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll('.hero-visual');
    parallaxElements.forEach(element => {
        const speed = 0.15;
        element.style.transform = `translateY(${scrolled * speed}px)`;
    });
});

// Dynamic typing effect for code lines
function startTypingAnimation() {
    const codeLines = document.querySelectorAll('.line');

    codeLines.forEach((line, index) => {
        setTimeout(() => {
            line.style.animation = 'none';
            line.offsetHeight; // Trigger reflow
            line.style.animation = 'typing 2s infinite ease-in-out';
        }, index * 500);
    });
}

// Start typing animation when hero is visible
let typingInterval = null;
const heroObserver = new IntersectionObserver(function (entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            startTypingAnimation();
            if (typingInterval) clearInterval(typingInterval);
            typingInterval = setInterval(startTypingAnimation, 8000);
            heroObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

document.addEventListener('DOMContentLoaded', function () {
    const heroSection = document.querySelector('.hero');
    if (heroSection) {
        heroObserver.observe(heroSection);
    }
});

// Form validation and submission
document.addEventListener('DOMContentLoaded', function () {
    const contactForm = document.querySelector('.contact-form');

    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();

            // Get form data
            const formData = new FormData(this);
            const name = formData.get('name');
            const email = formData.get('email');
            const subject = formData.get('subject');
            const message = formData.get('message');

            // Basic validation
            if (!name || !email || !message) {
                showNotification('Vui lòng điền đầy đủ thông tin bắt buộc!', 'error');
                return;
            }

            if (!isValidEmail(email)) {
                showNotification('Email không hợp lệ!', 'error');
                return;
            }

            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang gửi...';
            submitBtn.disabled = true;

            // Simulate form submission (replace with actual AJAX call)
            setTimeout(() => {
                showNotification('Tin nhắn đã được gửi thành công! Chúng tôi sẽ liên hệ với bạn sớm nhất.', 'success');
                contactForm.reset();
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 2000);
        });
    }
});

// Email validation function
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        </div>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'success' ? 'var(--primary-color)' : type === 'error' ? 'var(--secondary-color)' : 'var(--accent-color)'};
        color: var(--dark-bg);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        z-index: 9999;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        max-width: 400px;
        font-weight: 600;
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);

    // Close button functionality
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    });

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add loading screen
document.addEventListener('DOMContentLoaded', function () {
    // Create loading screen
    const loadingScreen = document.createElement('div');
    loadingScreen.className = 'loading-screen';
    loadingScreen.innerHTML = `
        <div class="loading-content">
            <div class="loading-logo">
                <i class="fas fa-gamepad"></i>
                <span>CHECKMXTFF</span>
            </div>
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
            <p>Đang khởi tạo Free Fire Tools...</p>
        </div>
    `;

    // Add loading styles
    loadingScreen.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: var(--dark-bg);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        transition: opacity 0.5s ease;
    `;

    const loadingContent = loadingScreen.querySelector('.loading-content');
    loadingContent.style.cssText = `
        text-align: center;
        color: var(--text-primary);
    `;

    const loadingLogo = loadingScreen.querySelector('.loading-logo');
    loadingLogo.style.cssText = `
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    `;

    const spinner = loadingScreen.querySelector('.spinner');
    spinner.style.cssText = `
        width: 50px;
        height: 50px;
        border: 3px solid rgba(0, 255, 136, 0.3);
        border-top: 3px solid var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    `;

    // Add spinner animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

    document.body.appendChild(loadingScreen);

    // Remove loading screen after page load
    window.addEventListener('load', function () {
        setTimeout(() => {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                if (loadingScreen.parentNode) {
                    loadingScreen.remove();
                }
            }, 500);
        }, 1000);
    });
});

// Add cursor trail effect
document.addEventListener('DOMContentLoaded', function () {
    const cursor = document.createElement('div');
    cursor.className = 'cursor-trail';
    cursor.style.cssText = `
        position: fixed;
        width: 20px;
        height: 20px;
        background: radial-gradient(circle, var(--primary-color), transparent);
        border-radius: 50%;
        pointer-events: none;
        z-index: 9998;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    document.body.appendChild(cursor);

    document.addEventListener('mousemove', function (e) {
        cursor.style.left = e.clientX - 10 + 'px';
        cursor.style.top = e.clientY - 10 + 'px';
        cursor.style.opacity = '0.6';
    });

    document.addEventListener('mouseleave', function () {
        cursor.style.opacity = '0';
    });
});

// Performance optimization: Debounce scroll events
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Apply debounce to scroll events for expensive ops
const debouncedScrollHandler = debounce(function () {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    const past = window.scrollY > 24;
    navbar.classList.toggle('shrink', past);
}, 50);

window.addEventListener('scroll', debouncedScrollHandler);

// THEME SWITCHER
(function () {
    const root = document.documentElement;
    const btn = document.getElementById('themeToggle');
    const THEMES = ['dark', 'light', 'neon'];

    function applyTheme(theme) {
        if (theme === 'dark') {
            root.removeAttribute('data-theme');
        } else {
            root.setAttribute('data-theme', theme);
        }
        if (btn) {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = theme === 'light' ? 'fas fa-moon' : theme === 'neon' ? 'fas fa-bolt' : 'fas fa-sun';
            }
        }
    }

    function getSavedTheme() {
        return localStorage.getItem('theme') || 'dark';
    }

    function saveTheme(theme) {
        localStorage.setItem('theme', theme);
    }

    document.addEventListener('DOMContentLoaded', () => {
        const saved = getSavedTheme();
        applyTheme(saved);
        if (btn) {
            btn.addEventListener('click', () => {
                const current = root.getAttribute('data-theme') || 'dark';
                const idx = THEMES.indexOf(current);
                const next = THEMES[(idx + 1) % THEMES.length];
                applyTheme(next);
                saveTheme(next);
            });
        }
    });
})();

// 3D TILT EFFECT
(function () {
    const maxTilt = 10; // degrees
    const perspective = 800;

    function handleMove(e, card) {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width; // 0..1
        const y = (e.clientY - rect.top) / rect.height; // 0..1
        const rotX = (0.5 - y) * (maxTilt * 2);
        const rotY = (x - 0.5) * (maxTilt * 2);
        card.style.transform = `perspective(${perspective}px) rotateX(${rotX}deg) rotateY(${rotY}deg)`;
        card.style.setProperty('--mx', `${x * 100}%`);
        card.style.setProperty('--my', `${y * 100}%`);
        card.style.setProperty('--glow-o', 1);
    }

    function reset(card) {
        card.style.transform = `perspective(${perspective}px) rotateX(0) rotateY(0)`;
        card.style.setProperty('--glow-o', 0);
    }

    document.addEventListener('DOMContentLoaded', () => {
        const cards = document.querySelectorAll('.tilt');
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => handleMove(e, card));
            card.addEventListener('mouseleave', () => reset(card));
            card.addEventListener('mouseenter', () => card.style.setProperty('--glow-o', 1));
            // Touch fallback
            card.addEventListener('touchmove', (e) => {
                const t = e.touches[0];
                handleMove(t, card);
            }, { passive: true });
            card.addEventListener('touchend', () => reset(card));
        });
    });
})();

// MAGNETIC BUTTONS
(function () {
    const strength = 20; // px pull

    function onMove(e, btn) {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${(x / rect.width) * strength}px, ${(y / rect.height) * strength}px)`;
    }
    function reset(btn) { btn.style.transform = 'translate(0, 0)'; }

    document.addEventListener('DOMContentLoaded', () => {
        const buttons = document.querySelectorAll('.magnetic');
        buttons.forEach(btn => {
            btn.addEventListener('mousemove', (e) => onMove(e, btn));
            btn.addEventListener('mouseleave', () => reset(btn));
            // Touch: small hover nudge
            btn.addEventListener('touchstart', () => btn.style.transform = 'translate(0, -2px)');
            btn.addEventListener('touchend', () => reset(btn));
        });
    });
})();

// HERO GALLERY SLIDER
(function () {
    const SELECTORS = {
        slider: '#heroSlider', prev: '#heroPrev', next: '#heroNext', slide: '.slide'
    };
    let idx = 0, slides = [], slider, prev, next, autoplay;

    function show(i) {
        if (!slides.length) return;
        idx = (i + slides.length) % slides.length;
        slides.forEach((s, n) => s.classList.toggle('active', n === idx));
    }
    function nextSlide() { show(idx + 1); }
    function prevSlide() { show(idx - 1); }

    function startAutoplay() {
        stopAutoplay();
        autoplay = setInterval(nextSlide, 5000);
    }
    function stopAutoplay() { if (autoplay) clearInterval(autoplay); }

    document.addEventListener('DOMContentLoaded', () => {
        slider = document.querySelector(SELECTORS.slider);
        prev = document.querySelector(SELECTORS.prev);
        next = document.querySelector(SELECTORS.next);
        slides = Array.from(document.querySelectorAll(SELECTORS.slide));
        if (!slider || !slides.length) return;

        show(0);
        startAutoplay();

        if (prev) prev.addEventListener('click', () => { prevSlide(); startAutoplay(); });
        if (next) next.addEventListener('click', () => { nextSlide(); startAutoplay(); });

        // Pause on hover
        slider.addEventListener('mouseenter', stopAutoplay);
        slider.addEventListener('mouseleave', startAutoplay);

        // Keyboard support
        slider.setAttribute('tabindex', '0');
        slider.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') { prevSlide(); startAutoplay(); }
            if (e.key === 'ArrowRight') { nextSlide(); startAutoplay(); }
        });
    });
})();

// FX: Snowfall / Particles
(function () {
    const TWO_PI = Math.PI * 2;
    let canvas, ctx, w, h, flakes = [], running = true;

    const cfg = {
        density: 0.00018, // flakes per pixel
        maxSize: 3.2,
        minSize: 0.8,
        wind: 0.15,
        gravity: 0.35,
        drift: 0.25
    };

    function themeColor() {
        const t = document.documentElement.getAttribute('data-theme');
        if (t === 'light') return 'rgba(0,0,0,0.5)';
        if (t === 'neon') return 'rgba(57,255,20,0.7)';
        return 'rgba(255,255,255,0.7)';
    }

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
        const target = Math.floor(w * h * cfg.density);
        flakes.length = Math.min(flakes.length, target);
        while (flakes.length < target) flakes.push(makeFlake());
    }

    function makeFlake() {
        return {
            x: Math.random() * w,
            y: Math.random() * h,
            r: cfg.minSize + Math.random() * (cfg.maxSize - cfg.minSize),
            vY: cfg.gravity * (0.5 + Math.random()),
            vX: (Math.random() - 0.5) * cfg.drift + cfg.wind,
            a: Math.random() * TWO_PI,
            aa: (Math.random() - 0.5) * 0.02
        };
    }

    function step() {
        if (!running) return;
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = themeColor();
        flakes.forEach(f => {
            f.a += f.aa;
            f.x += f.vX + Math.cos(f.a) * 0.2;
            f.y += f.vY + Math.sin(f.a) * 0.1;
            if (f.y > h + f.r) { f.y = -f.r; f.x = Math.random() * w; }
            if (f.x > w + f.r) { f.x = -f.r; }
            if (f.x < -f.r) { f.x = w + f.r; }
            ctx.beginPath();
            ctx.arc(f.x, f.y, f.r, 0, TWO_PI);
            ctx.closePath();
            ctx.fill();
        });
        requestAnimationFrame(step);
    }

    function init() {
        canvas = document.getElementById('fxCanvas');
        if (!canvas) return;
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        ctx = canvas.getContext('2d');
        resize();
        window.addEventListener('resize', resize);
        document.addEventListener('visibilitychange', () => { running = !document.hidden; if (running) step(); });
        const obs = new MutationObserver(step); // react to theme changes
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
        step();
    }

    document.addEventListener('DOMContentLoaded', init);
})();

// Initialize download button handlers
document.addEventListener('DOMContentLoaded', function () {
    // Setup download button event listeners
    const downloadButtons = document.querySelectorAll('.download-btn, .guide-btn');

    downloadButtons.forEach(button => {
        const cellRange = button.getAttribute('data-cell');
        const productName = button.getAttribute('data-product');

        if (cellRange && productName) {
            button.addEventListener('click', handleDownload(cellRange, productName));
        }
    });
});

/**
 * JavaScript xử lý cho Dabilux Nuôi Thân Widget
 */

function dabiluxNuoiThanToggle() {
    const widget = document.getElementById('dabilux-nuoi-than-widget');
    if (widget) {
        widget.classList.toggle('active');
    }
}

// Tự động đóng khi click ra ngoài
document.addEventListener('click', function (event) {
    const widget = document.getElementById('dabilux-nuoi-than-widget');
    if (!widget) return;

    const isClickInside = widget.contains(event.target);

    if (!isClickInside && widget.classList.contains('active')) {
        widget.classList.remove('active');
    }
});

// Floating Tooltip for disabled buttons
document.addEventListener('DOMContentLoaded', function () {
    const disabledButtons = document.querySelectorAll('.use-btn[data-tooltip]');

    disabledButtons.forEach(button => {
        const tooltipText = button.getAttribute('data-tooltip');
        
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'floating-tooltip';
        tooltip.textContent = tooltipText;
        tooltip.style.position = 'fixed';
        tooltip.style.zIndex = '9999';
        document.body.appendChild(tooltip);

        // Prevent link from working
        button.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        // Show tooltip on hover
        button.addEventListener('mouseenter', function (e) {
            tooltip.classList.add('show');
        });

        // Hide tooltip on mouse leave
        button.addEventListener('mouseleave', function () {
            tooltip.classList.remove('show');
        });

        // Follow mouse cursor
        button.addEventListener('mousemove', function (e) {
            const tooltipWidth = tooltip.offsetWidth;
            const tooltipHeight = tooltip.offsetHeight;
            tooltip.style.left = (e.clientX + 15) + 'px';
            tooltip.style.top = (e.clientY + 15) + 'px';
        });
    });
});