/* 
 * Self-hosted cookie consent banner
 * No external API dependencies - stores consent in localStorage
 */
ckan.module('cookie_banner', function (jQuery) {
    return {
        initialize: function () {
            var self = this;
            this.sandbox_ref = this.sandbox;
            
            // Check if user has already made a consent choice
            if (!this.hasConsent()) {
                this.showBanner();
            } else {
                // Apply previously saved consent
                this.applyConsent();
            }
            
            // Set up event handlers
            this.el.on('click', '.cookie-banner__accept-all', function(e) {
                e.preventDefault();
                self.acceptAll();
            });
            
            this.el.on('click', '.cookie-banner__reject', function(e) {
                e.preventDefault();
                self.rejectOptional();
            });
            
            this.el.on('click', '.cookie-banner__toggle-details', function(e) {
                e.preventDefault();
                self.toggleDetails();
            });
            
            this.el.on('change', '.cookie-banner__analytics-toggle', function(e) {
                self.saveCustomPreferences();
            });
            
            this.el.on('click', '.cookie-banner__close', function(e) {
                e.preventDefault();
                self.minimizeBanner();
            });
            
            this.el.on('click', '.cookie-banner__minimized', function(e) {
                e.preventDefault();
                self.showBanner();
            });
        },
        
        hasConsent: function() {
            return localStorage.getItem('cookie_consent') !== null;
        },
        
        getConsent: function() {
            var consent = localStorage.getItem('cookie_consent');
            return consent ? JSON.parse(consent) : null;
        },
        
        saveConsent: function(analytics) {
            var consent = {
                necessary: true,  // Always true
                analytics: analytics,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem('cookie_consent', JSON.stringify(consent));
            this.applyConsent();
        },
        
        applyConsent: function() {
            var consent = this.getConsent();
            if (consent && consent.analytics) {
                // Enable analytics
                this.sandbox_ref.publish('analytics_enabled', true);
            } else {
                // Disable analytics
                this.sandbox_ref.publish('analytics_enabled', false);
            }
        },
        
        acceptAll: function() {
            this.saveConsent(true);
            this.hideBanner();
        },
        
        rejectOptional: function() {
            this.saveConsent(false);
            this.hideBanner();
        },
        
        saveCustomPreferences: function() {
            var analyticsEnabled = this.el.find('.cookie-banner__analytics-toggle').is(':checked');
            this.saveConsent(analyticsEnabled);
            this.hideBanner();
        },
        
        showBanner: function() {
            this.el.removeClass('cookie-banner--minimized');
            this.el.addClass('cookie-banner--visible');
            
            // Pre-populate checkbox if consent exists
            var consent = this.getConsent();
            if (consent) {
                this.el.find('.cookie-banner__analytics-toggle').prop('checked', consent.analytics);
            }
        },
        
        hideBanner: function() {
            this.el.removeClass('cookie-banner--visible');
            this.el.addClass('cookie-banner--hidden');
            
            // After animation, show minimized version
            var self = this;
            setTimeout(function() {
                self.el.removeClass('cookie-banner--hidden');
                self.el.addClass('cookie-banner--minimized');
            }, 500);
        },
        
        minimizeBanner: function() {
            this.el.removeClass('cookie-banner--visible');
            this.el.addClass('cookie-banner--minimized');
        },
        
        toggleDetails: function() {
            var details = this.el.find('.cookie-banner__details');
            var toggleBtn = this.el.find('.cookie-banner__toggle-details');
            
            if (details.hasClass('cookie-banner__details--visible')) {
                details.removeClass('cookie-banner__details--visible');
                toggleBtn.text('Details anzeigen');
            } else {
                details.addClass('cookie-banner__details--visible');
                toggleBtn.text('Details ausblenden');
            }
        }
    };
});
