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

			input.bind('keyup', this._onChange);

		},
		_onChange: function (event) {
			var nav = this.el.find('nav');
			nav.scrollTop(0);

			var options = this.options;
			var queryText = event.target.value.toLowerCase();

			var listItems = options[options.facet];

			listItems.removeClass("search");

			var searchedItems = listItems.filter(function () {
				var itemLabel = $(this).find("span.item-label").text().trim().toLowerCase();
				return (
					itemLabel.startsWith(queryText.toLowerCase()) ||
					(queryText.length >= 3 && itemLabel.indexOf(queryText) !== -1)
				);
			})

			searchedItems.each(function () {
				$(this).toggleClass("search", queryText !== "");
			});

			var listEl = this.el.find('nav ul');
			if (searchedItems.length === 0 && queryText !== "") {
				listEl.replaceWith("<ul><span class='item-label no-results'>No results found</span> </ul> ");
			} else if (searchedItems.length === 0 && queryText === "") {
				var resetItems = options[options.facet].clone();
				listEl.find("span.no-results").remove();
				listEl.empty().append(resetItems);
			} else {
				listEl.find("span.no-results").remove();
				listEl.prepend(searchedItems).addClass('list-unstyled nav nav-simple nav-facet');
			}
		}
	}
});
