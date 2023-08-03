// Create ckan js module 
this.ckan.module('facet-search', function (jQuery, _) {
	return {
		options: {
			facet: null,
		},
		initialize: function () {
			jQuery.proxyAll(this, /_on/);

			facet = this.options.facet;
			var input = this.el.find('input.facet-search-' + facet);

			// Backups of the list items in options	 
			var listItems = this.el.find('nav ul li');
			this.options[facet] = listItems;

			input.bind('change paste keyup', this._onChange);

		},
		_onChange: function (event) {
			var nav = this.el.find('nav');
			nav.scrollTop(0);

			var options = this.options;
			var queryText = event.target.value.toLowerCase();

			var listItems = options[options.facet];
			var targetItems = listItems.filter(function () {
				return $(this).find("span.item-label").text().trim().toLowerCase().indexOf(queryText.toLowerCase()) > -1;
			});

			targetItems.each(function () {
				$(this).toggleClass("search", queryText !== "");
			});

			var listEl = this.el.find('nav ul');
			if (targetItems.length === 0 && queryText !== "") {
				listEl.replaceWith("<ul><span class='item-label no-results'>No results found</span> </ul> ");
			} else if (targetItems.length === 0 && queryText === "") {
				var newItems = options[options.facet].clone();
				listEl.find("span.no-results").remove();
				listEl.empty().append(newItems);
			} else {
				listEl.find("span.no-results").remove();
				listEl.prepend(targetItems).addClass('list-unstyled nav nav-simple nav-facet');
			}
		}
	}
});
