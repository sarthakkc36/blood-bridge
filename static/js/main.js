// Wait for DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Form validation
    initializeFormValidation();
    
    // Blood stock chart initialization (if on admin dashboard)
    initializeBloodStockChart();
    
    // Flash message auto-dismiss
    setupFlashMessages();
    
    // Password strength meter
    setupPasswordStrengthMeter();
    
    // Animated elements on scroll
    setupScrollAnimations();
    
    // Navbar active state
    setActiveNavItem();
    
    // Mobile menu handling
    setupMobileMenu();
});

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

function initializeBloodStockChart() {
    const chartCanvas = document.getElementById('bloodStockChart');
    if (chartCanvas) {
        const ctx = chartCanvas.getContext('2d');
        
        // Blood type data
        const bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
        const currentStock = [65, 45, 75, 35, 25, 15, 85, 55];
        const optimalStock = [100, 70, 100, 60, 50, 40, 120, 80];
        
        // Create gradient for bars
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(220, 53, 69, 0.8)');
        gradient.addColorStop(1, 'rgba(220, 53, 69, 0.4)');
        
        new Chart(chartCanvas, {
            type: 'bar',
            data: {
                labels: bloodTypes,
                datasets: [
                    {
                        label: 'Current Stock (units)',
                        data: currentStock,
                        backgroundColor: gradient,
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1,
                        borderRadius: 5,
                    },
                    {
                        label: 'Optimal Stock Level',
                        data: optimalStock,
                        type: 'line',
                        borderColor: 'rgba(0, 123, 255, 0.7)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(0, 123, 255, 0.8)',
                        pointRadius: 4,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y + ' units';
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Units'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Blood Type'
                        }
                    }
                }
            }
        });
    }
    
    // For donor/receiver dashboard blood availability visualization
    const bloodProgress = document.querySelectorAll('.blood-type .progress-bar');
    if (bloodProgress.length > 0) {
        bloodProgress.forEach(bar => {
            const width = bar.style.width;
            const percentage = parseInt(width);
            
            if (percentage < 30) {
                bar.classList.remove('bg-success', 'bg-warning');
                bar.classList.add('bg-danger');
            } else if (percentage < 60) {
                bar.classList.remove('bg-success', 'bg-danger');
                bar.classList.add('bg-warning');
            } else {
                bar.classList.remove('bg-warning', 'bg-danger');
                bar.classList.add('bg-success');
            }
        });
    }
}

function setupFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(message => {
        const closeButton = message.querySelector('.btn-close');
        setTimeout(() => {
            if (message) {
                const dismissAlert = new bootstrap.Alert(message);
                dismissAlert.close();
            }
        }, 5000);
        
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                const dismissAlert = new bootstrap.Alert(message);
                dismissAlert.close();
            });
        }
    });
}

function setupPasswordStrengthMeter() {
    const passwordInput = document.querySelector('input[name="password"]');
    if (passwordInput) {
        // Create strength meter element if it doesn't exist
        let strengthMeter = document.getElementById('password-strength');
        if (!strengthMeter) {
            const meterContainer = document.createElement('div');
            meterContainer.className = 'progress mt-2';
            meterContainer.style.height = '5px';
            
            strengthMeter = document.createElement('div');
            strengthMeter.id = 'password-strength';
            strengthMeter.className = 'progress-bar';
            strengthMeter.role = 'progressbar';
            
            meterContainer.appendChild(strengthMeter);
            passwordInput.parentNode.appendChild(meterContainer);
            
            const strengthText = document.createElement('div');
            strengthText.id = 'password-strength-text';
            strengthText.className = 'small mt-1';
            passwordInput.parentNode.appendChild(strengthText);
        }
        
        passwordInput.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            updatePasswordStrengthIndicator(strength);
        });
    }
}

function calculatePasswordStrength(password) {
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength += 1;
    
    // Character variety checks
    if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength += 1;
    if (password.match(/\d/)) strength += 1;
    if (password.match(/[^a-zA-Z\d]/)) strength += 1;
    
    return strength;
}

function updatePasswordStrengthIndicator(strength) {
    const indicator = document.getElementById('password-strength');
    const strengthText = document.getElementById('password-strength-text');
    
    if (indicator && strengthText) {
        const strengthLabels = ['Weak', 'Fair', 'Good', 'Strong'];
        const strengthClasses = ['danger', 'warning', 'info', 'success'];
        
        if (strength > 0) {
            indicator.className = `progress-bar bg-${strengthClasses[strength-1]}`;
            indicator.style.width = `${strength * 25}%`;
            strengthText.textContent = strengthLabels[strength-1];
            strengthText.className = `small mt-1 text-${strengthClasses[strength-1]}`;
        } else {
            indicator.className = 'progress-bar';
            indicator.style.width = '0%';
            strengthText.textContent = '';
        }
    }
}

function setupScrollAnimations() {
    // Simple scroll animation for elements
    const fadeElements = document.querySelectorAll('.fade-in-element');
    
    const fadeInOnScroll = () => {
        fadeElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < window.innerHeight - elementVisible) {
                element.classList.add('visible');
            }
        });
    };
    
    window.addEventListener('scroll', fadeInOnScroll);
    // Initial check
    fadeInOnScroll();
}

function setActiveNavItem() {
    // Get current path
    const path = window.location.pathname;
    
    // Find all nav links
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    // Match with the closest link
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === path) {
            link.classList.add('active');
        }
    });
}

function setupMobileMenu() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            document.querySelector('.navbar-collapse').classList.toggle('show');
        });
    }
}

// Blood compatibility calculator
function calculateBloodCompatibility(bloodType) {
    const compatibility = {
        'A+': ['A+', 'AB+'],
        'A-': ['A+', 'A-', 'AB+', 'AB-'],
        'B+': ['B+', 'AB+'],
        'B-': ['B+', 'B-', 'AB+', 'AB-'],
        'AB+': ['AB+'],
        'AB-': ['AB+', 'AB-'],
        'O+': ['A+', 'B+', 'AB+', 'O+'],
        'O-': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    };
    
    return compatibility[bloodType] || [];
}

// Function to check eligibility based on common criteria
function checkEligibility(formData) {
    const eligibilityResults = {
        eligible: true,
        reasons: []
    };
    
    // Age check (16-65 years)
    const age = formData.age;
    if (age < 16) {
        eligibilityResults.eligible = false;
        eligibilityResults.reasons.push('You must be at least 16 years old to donate blood.');
    } else if (age > 65) {
        eligibilityResults.eligible = false;
        eligibilityResults.reasons.push('Donors over 65 may require additional medical assessment.');
    }
    
    // Weight check (min 50kg/110lbs)
    const weight = formData.weight;
    if (weight < 50) {
        eligibilityResults.eligible = false;
        eligibilityResults.reasons.push('You must weigh at least 50kg (110lbs) to donate blood.');
    }
    
    // Recent donation check (56 days)
    const lastDonation = formData.lastDonation;
    if (lastDonation) {
        const lastDonationDate = new Date(lastDonation);
        const today = new Date();
        const daysSinceLastDonation = Math.floor((today - lastDonationDate) / (1000 * 60 * 60 * 24));
        
        if (daysSinceLastDonation < 56) {
            eligibilityResults.eligible = false;
            eligibilityResults.reasons.push(`You must wait at least 56 days between whole blood donations. It has been ${daysSinceLastDonation} days since your last donation.`);
        }
    }
    
    // Other health conditions check
    const healthConditions = formData.healthConditions || [];
    const criticalConditions = ['active_cancer', 'heart_disease', 'hiv', 'hepatitis'];
    
    healthConditions.forEach(condition => {
        if (criticalConditions.includes(condition)) {
            eligibilityResults.eligible = false;
            eligibilityResults.reasons.push('One or more health conditions may prevent you from donating blood.');
        }
    });
    
    return eligibilityResults;
}

// Blood stock status checker
function getBloodStockStatus(units) {
    if (units <= 20) {
        return { status: 'critical', class: 'danger', message: 'Critical - Urgent donations needed' };
    } else if (units <= 50) {
        return { status: 'low', class: 'warning', message: 'Low - Donations encouraged' };
    } else {
        return { status: 'normal', class: 'success', message: 'Normal - Healthy stock levels' };
    }
}

// Format dates in a readable format
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Calculate next eligible donation date
function calculateNextDonationDate(lastDonationDate) {
    const lastDate = new Date(lastDonationDate);
    const nextDate = new Date(lastDate);
    nextDate.setDate(lastDate.getDate() + 56);
    return nextDate;
}

// Sanitize user input
function sanitizeInput(input) {
    return input.replace(/[<>]/g, '');
}

// Toggle theme if we add a dark mode feature
function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const isDarkMode = document.body.classList.contains('dark-theme');
    localStorage.setItem('darkMode', isDarkMode);
}

// Check if dark mode is enabled in localStorage
function checkThemePreference() {
    const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
    if (darkModeEnabled) {
        document.body.classList.add('dark-theme');
    }
}

// Initialize eligibility quiz if it exists on the page
function initializeEligibilityQuiz() {
    const quizContainer = document.getElementById('eligibilityQuiz');
    if (quizContainer) {
        const startBtn = document.querySelector('[data-bs-target="#eligibilityQuiz"]');
        const quizForm = document.getElementById('eligibilityForm');
        
        if (quizForm) {
            quizForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(quizForm);
                const formObject = {};
                
                formData.forEach((value, key) => {
                    formObject[key] = value;
                });
                
                const eligibilityResults = checkEligibility(formObject);
                displayEligibilityResults(eligibilityResults);
            });
        }
    }
}

// Display eligibility results
function displayEligibilityResults(results) {
    const resultsContainer = document.getElementById('eligibilityResults');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
        
        const resultCard = document.createElement('div');
        resultCard.className = `card border-${results.eligible ? 'success' : 'danger'} mb-3`;
        
        const cardHeader = document.createElement('div');
        cardHeader.className = `card-header bg-${results.eligible ? 'success' : 'danger'} text-white`;
        cardHeader.textContent = results.eligible ? 'You are eligible to donate blood!' : 'You may not be eligible to donate blood at this time';
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        if (results.reasons.length > 0) {
            const reasonsList = document.createElement('ul');
            reasonsList.className = 'list-group list-group-flush mt-3';
            
            results.reasons.forEach(reason => {
                const reasonItem = document.createElement('li');
                reasonItem.className = 'list-group-item';
                reasonItem.textContent = reason;
                reasonsList.appendChild(reasonItem);
            });
            
            cardBody.appendChild(reasonsList);
        }
        
        const actionText = document.createElement('p');
        actionText.className = 'mt-3';
        actionText.textContent = results.eligible ? 
            'You can proceed with scheduling your blood donation.' : 
            'Please consult with a healthcare professional for more information about your eligibility.';
        
        cardBody.appendChild(actionText);
        
        resultCard.appendChild(cardHeader);
        resultCard.appendChild(cardBody);
        
        resultsContainer.appendChild(resultCard);
    }
}