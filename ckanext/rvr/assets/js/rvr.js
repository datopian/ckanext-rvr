// Description: Custom JS for RVR theme
this.ckan.module('arrow-dropdown', function (jQuery, _) {
  return {
    options: {
      arrow: null
    },
    initialize: function () {
      this.el.select2({
        minimumResultsForSearch: Infinity
      });
    }
  };
});

// group dropdown arrow
this.ckan.module('auto-complete-arrow', function ($, _) {
  return {
    initialize: function () {
      this.el.addClass('multi-arrow');
      this.el.css('position', 'relative');

      this.el.on('click', function (event) {
        const input = $(event.target).closest('.multi-arrow').find('input');
        if (input.length) {
          input.click();
        }
      });
    }
  };
});

// tooltip module
this.ckan.module('tooltip', function ($, _) {
  return {
    initialize: function () {
      var element = this.el[0]; // Assuming this.el is a jQuery object

      // Check if the element is disabled
      if (element.disabled) {
        // Create a wrapper div around the disabled element
        var wrapper = document.createElement('div');
        wrapper.style.display = 'inline-block';
        wrapper.style.position = 'relative';
        element.parentNode.insertBefore(wrapper, element);
        wrapper.appendChild(element);

        var tooltip = new bootstrap.Tooltip(element, {
          container: 'body'
        });
        wrapper.addEventListener('mouseenter', function () {
          tooltip.show();
        });

        wrapper.addEventListener('mouseleave', function () {
          tooltip.hide();
        });
      } else {
        var tooltip = new bootstrap.Tooltip(element, {
          container: 'body'
        });
      }
    }
  };
});

// Dataset clientside validation
this.ckan.module('dataset-custom-validator', function ($, _) {
  return {
    initialize: function () {
      $.proxyAll(this, /_on/);
      this.el.on('submit', this._onSubmit);
    },
    _onSubmit: function (event) {
      const el = this.el[0];

      // Create new error block element
      const errorBlock = document.createElement('div');
      errorBlock.className = 'error-explanation alert alert-error';
      errorBlock.innerHTML = '<p>Das Formular enthält unzulässige Einträge:</p>';
      const errorList = document.createElement('ul');
      errorBlock.appendChild(errorList);

      // Mandatory fields validation error on tooltip
      const fieldTitle = el.querySelector('#field-title');
      const fieldGroupsId = el.querySelector('#field-groups');
      const fieldOrganizations = el.querySelector('#field-organizations');
      const fieldNotes = el.querySelector('#field-notes');
      const fieldsList = [fieldTitle, fieldGroupsId, fieldOrganizations, fieldNotes];

      const errors = {
        'field-title': 'Name: Fehlender Wert',
        'field-groups': 'Beschreibung: Fehlender Wert',
        'field-organizations': 'Gruppen: Fehlender Wert',
        'field-notes': 'Organisation: Fehlender Wert'
      };

      let hasErrors = false;

      fieldsList.forEach(field => {
        if (!field.value.trim()) {
          hasErrors = true;

          // Add error message to the error list
          const li = document.createElement('li');
          li.textContent = errors[field.id];
          errorList.appendChild(li);

          // Add error block after the field if not already present
          if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('error-block')) {
            field.insertAdjacentHTML('afterend', `<span class="error-block">${errors[field.id]}</span>`);
          }

          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          field.scrollIntoView({ behavior: 'smooth', block: 'center' });
          field.focus();
          event.preventDefault();
        }
      });

      // Insert error block at the top of the form if there are errors and it's not already present
      if (hasErrors && !el.querySelector('.error-explanation')) {
        el.insertBefore(errorBlock, el.firstChild);
      }

      // Enable the submit button after a delay
      setTimeout(() => {
        const submitBtn = this.el.find('button[name="save"]');
        submitBtn[0].disabled = false;
      }, 1000);
    },
  };
});

// Hide and show homepage svg map
this.ckan.module('home-svg-map-search', function ($, _) {

  options = {
    action: null
  };

  return {
    initialize: function () {
      $.proxyAll(this, /_on/);
      this.el.on('click', this._onClick);
    },

    _onClick: function (event) {
      event.preventDefault();
      var action = this.options.action;
      if (action === 'show') {
        var mapMaximized = document.getElementById("maximized");
        var mapMinimized = document.getElementById("minimized");
        mapMaximized.style.display = "block";
        mapMinimized.style.display = "none";
      } else if (action === 'hide') {
        var mapMaximized = document.getElementById("maximized");
        var mapMinimized = document.getElementById("minimized");
        mapMaximized.style.display = "none";
        mapMinimized.style.display = "block";
      }
    },
  };

});
