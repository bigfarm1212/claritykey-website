// Supabase Configuration
const SUPABASE_URL = 'https://ehdwjvqwgkjfrquqwehj.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVoZHdqdnF3Z2tqZnJxdXF3ZWhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2NDQ5MDMsImV4cCI6MjA4ODIyMDkwM30.qQ8J3yKBnqxz6XnjD7JkZSxFaBH87XTs5DLpa34yJvA';
let supabaseClient = null;

if (SUPABASE_URL !== 'YOUR_SUPABASE_URL') {
    supabaseClient = window.supabase ? window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;
}

// Auth State Management
let currentSession = null;

async function checkAuthState() {
    if (!supabaseClient) return;

    const { data: { session } } = await supabaseClient.auth.getSession();
    currentSession = session;
    updateNavUI(session);

    // Listen for auth changes (real-time updates)
    supabaseClient.auth.onAuthStateChange((event, session) => {
        currentSession = session;
        updateNavUI(session);
    });
}

async function updateNavUI(session) {
    const signinLink = document.getElementById('signin-link');
    const signupLink = document.getElementById('signup-link');
    const subscriptionLink = document.getElementById('subscription-link');

    if (session) {
        // Logged In: Show Email and Hide Sign Up
        if (signinLink) {
            let emailText = session.user.email;
            let isUnlimited = false;

            // Check subscription status
            if (supabaseClient) {
                const { data, error } = await supabaseClient
                    .from('profiles')
                    .select('subscription_status')
                    .eq('id', session.user.id)
                    .single();

                if (data && data.subscription_status === 'unlimited') {
                    emailText += ' ✨';
                    isUnlimited = true;
                }
            }

            signinLink.innerText = emailText;
            signinLink.href = '#';
            signinLink.style.fontWeight = '700';
            signinLink.onclick = async (e) => {
                e.preventDefault();
                if (confirm('Do you want to log out?')) {
                    await supabaseClient.auth.signOut();
                    window.location.reload();
                }
            };

            // Show subscription link only for unlimited users
            if (subscriptionLink) {
                subscriptionLink.style.display = isUnlimited ? 'block' : 'none';
            }
        }
        if (signupLink) {
            signupLink.parentNode.style.display = 'none';
        }
    } else {
        // Not Logged In: Only show "Sign In"
        if (signupLink) {
            signupLink.parentNode.style.display = 'none';
        }
        if (signinLink) {
            signinLink.innerText = 'Sign In';
            signinLink.href = 'auth.html';
            signinLink.style.fontWeight = 'normal';
            signinLink.onclick = null;
        }
        if (subscriptionLink) {
            subscriptionLink.style.display = 'none';
        }
    }
}

// Global listener for downloads to handle protection and SmartScreen Modal
document.addEventListener('click', (e) => {
    const downloadBtn = e.target.closest('a[href*=".exe"]');
    if (downloadBtn && !downloadBtn.hasAttribute('data-direct-download')) {
        e.preventDefault();

        // 1. Check Auth FIRST
        if (!currentSession) {
            window.location.href = 'auth.html';
            return;
        }

        // 2. If authenticated, show the SmartScreen Modal
        const modal = document.getElementById('smartscreen-modal');
        if (modal) {
            modal.style.display = 'flex';
            const confirmBtn = document.getElementById('smartscreen-confirm-btn');
            if (confirmBtn) {
                confirmBtn.href = downloadBtn.href;
            }
        }
    }
});

// Setup SmartScreen Modal Close Logic
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('smartscreen-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal || e.target.closest('.smartscreen-close')) {
                modal.style.display = 'none';
            }
        });

        const confirmBtn = document.getElementById('smartscreen-confirm-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 1000); // Close automatically after they click download
            });
        }
    }
});

// Stripe Checkout Redirection
document.addEventListener('DOMContentLoaded', () => {
    const unlimitedBtn = document.getElementById('unlimited-btn');
    if (unlimitedBtn) {
        unlimitedBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!currentSession) {
                // Redirect to signup if not logged in
                window.location.href = 'auth.html?signup=true';
                return;
            }
            // Replace with actual Stripe Payment Link
            const STRIPE_PAYMENT_LINK = 'https://buy.stripe.com/4gM4gBeA27rQ8v5btwbjW02';
            const userId = currentSession.user.id;
            const userEmail = currentSession.user.email;

            // Redirect to Stripe, appending the Supabase User ID and prefilled email
            const checkoutUrl = new URL(STRIPE_PAYMENT_LINK);
            checkoutUrl.searchParams.append('client_reference_id', userId);
            checkoutUrl.searchParams.append('prefilled_email', userEmail);

            window.location.href = checkoutUrl.toString();
        });
    }

    checkAuthState();

    // --- Video Modal Logic ---
    const videoModal = document.getElementById('video-modal');
    const videoClose = document.getElementById('video-close');
    const demoVideo = document.getElementById('demo-video');
    const seeHowItWorksBtn = document.getElementById('see-how-it-works-btn');

    if (seeHowItWorksBtn && videoModal && demoVideo) {
        seeHowItWorksBtn.addEventListener('click', (e) => {
            e.preventDefault();
            // Using embed link with autoplay
            demoVideo.src = "https://www.youtube.com/embed/4J6pJ9Hr8fU?autoplay=1";
            videoModal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        });
    }

    if (videoClose && videoModal && demoVideo) {
        videoClose.addEventListener('click', () => {
            videoModal.style.display = 'none';
            demoVideo.src = ""; // Stop the video
            document.body.style.overflow = 'auto';
        });
    }

    // Close on click outside
    if (videoModal) {
        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) {
                videoModal.style.display = 'none';
                demoVideo.src = "";
                document.body.style.overflow = 'auto';
            }
        });
    }
});

// Simple micro-interaction for clay button clicks
document.querySelectorAll('.clay-button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if (btn.textContent.includes('Download') || btn.textContent.includes('Get for Windows')) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '✓ Downloading...';
            btn.style.transform = 'translateY(1px)';

            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.style.transform = '';
            }, 2500);
        }
    });
});

// Smooth Scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Demo Animation Logic
const demoText = document.getElementById('demo-text');
const aiBadge = document.getElementById('ai-badge');
const demoCursor = document.getElementById('demo-cursor');
const keypressInd = document.getElementById('keypress-indicator');

if (demoText && aiBadge && demoCursor && keypressInd) {
    const originalContent = '<span class="selection-highlight">Ths is a test sentance with some mistaks.</span>';
    const workingContent = '<span class="selection-highlight working">Ths is a test sentance with some mistaks.</span>';
    const correctedContent = '<span style="color: var(--accent-green); font-weight: 700;">This is a test sentence with some mistakes.</span> ✨';
    const cleanContent = 'Ths is a test sentance with some mistaks.';

    function step(fn, delay) {
        return new Promise(resolve => {
            setTimeout(() => {
                fn();
                resolve();
            }, delay);
        });
    }

    async function runDemoLoop() {
        // Reset
        demoText.innerHTML = cleanContent;
        demoCursor.style.opacity = '0';
        demoCursor.style.top = '20%';
        demoCursor.style.left = '10%';
        demoCursor.className = '';
        keypressInd.classList.remove('visible');
        aiBadge.classList.remove('visible');

        await step(() => {
            demoCursor.classList.add('visible');
            demoCursor.style.top = '45%';
            demoCursor.style.left = '10%';
        }, 1000);

        // Move to start of selection (start of "Ths")
        await step(() => {
            demoCursor.style.left = '12%';
            demoCursor.style.top = '52%';
        }, 1200);

        // Drag selection to end
        await step(() => {
            demoCursor.style.left = '88%';
            demoText.innerHTML = originalContent;
        }, 1000);

        // Press Ctrl + C
        await step(() => {
            keypressInd.textContent = 'Pressing Ctrl + C';
            keypressInd.classList.add('visible');
        }, 800);

        // Show AI Badge
        await step(() => {
            keypressInd.classList.remove('visible');
            aiBadge.classList.add('visible');
            demoText.innerHTML = workingContent;
        }, 1500);

        // Press Ctrl + V
        await step(() => {
            aiBadge.classList.remove('visible');
            keypressInd.textContent = 'Pressing Ctrl + V';
            keypressInd.classList.add('visible');
            demoCursor.style.opacity = '0';
        }, 2200);

        // Show corrected
        await step(() => {
            keypressInd.classList.remove('visible');
            demoText.innerHTML = correctedContent;
        }, 1200);

        // Hold and repeat
        setTimeout(runDemoLoop, 4000);
    }

    runDemoLoop();
}

// Carousel Logic
const track = document.querySelector('.carousel-track');
const dots = document.querySelectorAll('.nav-dot');
let currentIndex = 0;
let autoPlayInterval;

if (track && dots.length > 0) {
    function updateCarousel(index) {
        currentIndex = index;
        const offset = index * -100;
        track.style.transform = `translateX(calc(${offset}% - ${index * 2}rem))`;

        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === index);
        });
    }

    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            const index = parseInt(dot.dataset.index);
            updateCarousel(index);
            resetAutoPlay();
        });
    });

    function nextSlide() {
        currentIndex = (currentIndex + 1) % dots.length;
        updateCarousel(currentIndex);
    }

    function startAutoPlay() {
        autoPlayInterval = setInterval(nextSlide, 20000); // Wait 20 seconds
    }

    function resetAutoPlay() {
        clearInterval(autoPlayInterval);
        startAutoPlay();
    }

    startAutoPlay();
}
