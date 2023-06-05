ckan.module('civic_cookies', function (jQuery) {
    return {
      initialize: function () {
        
        ckan_sandbox = this.sandbox;
        
        var config = {
            apiKey: this.options.api_key,
            product: this.options.licence_type,
            position: this.options.popup_position,
            theme: this.options.theme_color,
            initialState: this.options.initial_state,
            necessaryCookies: ['ckan','1P_JAR', 'fldt', 'auth_tkt'],
            encodeCookie: true,
            notifyOnce: true,
            rejectButton: true,
            text: {
              on: "ein",
              off: "aus",
              title: 'Diese Website verwendet Cookies.',
              intro: 'Einige dieser Cookies sind notwendig, während andere uns helfen, Ihre Erfahrung zu verbessern, indem sie uns Einblicke in Ihre Nutzung der Website geben.',
              necessaryTitle: 'Notwendige Cookies',
              accept: "Alle Cookies akzeptieren",
              reject: "Nicht notwendige Cookies ablehnen",
              acceptSettings: "Alle Cookies akzeptieren",
              rejectSettings: "Nicht notwendige Cookies ablehnen",
              necessaryDescription: 'Notwendige Cookies ermöglichen Kernfunktionen wie Sicherheit, Netzwerkmanagement und Zugänglichkeit. Sie können diese deaktivieren, indem Sie die Einstellungen Ihres Browsers ändern, was jedoch die Funktionsweise der Website beeinträchtigen kann.              ',
            },
            accessibility:{
              accessKey: '',
              highlightFocus: true
            },
            optionalCookies: [
              {
                  name : 'analytics',
                  label: 'Analytische Cookies',
                  description: "Analyse-Cookies helfen uns, unsere Website zu verbessern, indem sie Informationen über die Nutzung der Website sammeln und melden. Die Cookies sammeln Informationen in einer Weise, die niemanden direkt identifiziert.                  ",
                  cookies: ['_pk_cvar.*', '_pk_id.*', '_pk_ses.*'],
                  onAccept : function(){
                    ckan_sandbox.publish('analytics_enabled', true);
                  },
                  onRevoke: function(){
                    ckan_sandbox.publish('analytics_enabled', false);
                  }
              },
            ]
        };
          
        CookieControl.load( config );
      }
    };
});