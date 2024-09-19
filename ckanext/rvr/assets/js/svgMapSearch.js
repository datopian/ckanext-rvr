// SVG Map Search helpers
function maximizeMap() {
  var mapMaximized = document.getElementById("maximized");
  var mapMinimized = document.getElementById("minimized");
  mapMaximized.style.display = "block";
  mapMinimized.style.display = "none";
}

function minimizeMap() {
  var mapMaximized = document.getElementById("maximized");
  var mapMinimized = document.getElementById("minimized");
  mapMaximized.style.display = "none";
  mapMinimized.style.display = "block";
}

// Mandatory fields helpers
function getSelectedOptions(sel) {
  var opts = [],
    opt;
  var len = sel.options.length;
  for (var i = 0; i < len; i++) {
    opt = sel.options[i];

    if (opt.selected) {
      opts.push(opt.value);
    }
  }

  opts = opts.filter(function (item, pos) {
    return opts.indexOf(item) == pos;
  });

  var group_string = document.getElementsByName("group_string")[0].value = opts.join("___");

  return group_string;
}

function checkTitle() {
  const titleElement = document.getElementById("field-title");
  if (!titleElement || titleElement.value == "") {
    return false;
  }
}

function checkGroups() {
  const groupsElement = document.getElementById("field-groups__1__id");
  if (!groupsElement || groupsElement.value == "") {
    return false;
  }
}

function checkOrg() {
  const orgElement = document.getElementById("field-organizations");
  if (!orgElement || orgElement.value == "") {
    return false;
  }
}

function checkNotes() {
  const notesElement = document.getElementById("field-notes");
  if (!notesElement || notesElement.value == "") {
    return false;
  }
}

function checkAll() {
  if (checkTitle() == false || checkGroups() == false || checkOrg() == false || checkNotes() == false) {
    return false;
  } else {
    return true;
  }
}

function setButtonTooltip() {
  var error_title = "";
  var error_notes = "";
  var error_groups = "";
  var error_org = "";

  if (checkTitle() == false) {
    error_title = "\tName: Fehlender Wert\n";
  }
  if (checkNotes() == false) {
    error_notes = "\tBeschreibung: Fehlender Wert\n";
  }
  if (checkGroups() == false) {
    error_groups = "\tGruppen: Fehlender Wert\n";
  }
  if (checkOrg() == false) {
    error_org = "\tOrganisation: Fehlender Wert\n";
  }

  var error_message = "Das Formular enthält unzulässige Einträge:\n" + error_title + error_notes + error_org + error_groups;

  return error_message;
}

function groupChange() {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
}

function orgChange() {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to disabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
    document.getElementsByClassName("btn btn-primary")[0].title = "";
  }
}

const fieldNotesElement = document.getElementById("field-notes");
if (fieldNotesElement) {
  fieldNotesElement.addEventListener("change", function (event) {
    if (checkAll() == false) {
      // Set the button class="btn btn-primary" in div class="form-actions" to disabled
      document.getElementsByClassName("btn btn-primary")[0].disabled = true;
      // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
      document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
    } else {
      // Set the button class="btn btn-primary" in div class="form-actions" to enabled
      document.getElementsByClassName("btn btn-primary")[0].disabled = false;
      document.getElementsByClassName("btn btn-primary")[0].title = "";
    }
  });
}



const fieldTitleElement = document.getElementById("field-notes");
if (fieldTitleElement) {
  fieldTitleElement.addEventListener("change", function (event) {
    if (checkAll() == false) {
      // Set the button class="btn btn-primary" in div class="form-actions" to disabled
      document.getElementsByClassName("btn btn-primary")[0].disabled = true;
      // Set the tooltip of the button class="btn btn-primary" in div class="form-actions" to the error message
      document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
    } else {
      // Set the button class="btn btn-primary" in div class="form-actions" to enabled
      document.getElementsByClassName("btn btn-primary")[0].disabled = false;
      document.getElementsByClassName("btn btn-primary")[0].title = "";
    }
  });
}

// On submit form event listener
const DatasetEditElement = document.getElementById("dataset-edit");
if (DatasetEditElement) {
  DatasetEditElement.addEventListener("submit", function (event) {
    // Get selected options from the element with id="field-groups__0__id"
    var selectedOptions = getSelectedOptions(document.getElementById("field-groups__1__id"));
    var groups_dict = [];
    //  Frome selectedOptions string to array
    var selectedOptionsArray = selectedOptions.split("___");
    // Loop through the selectedOptionsArray and add the group object to the groups_dict
    for (var i = 0; i < selectedOptionsArray.length; i++) {
      groups_dict[i] = { "id": selectedOptionsArray[i] };
    }
    // Set the value of the field with name="group_string" to the selectedOptions array
    document.getElementsByName("group_string")[0].value = selectedOptions;
  })
};

// On body change event listener
document.addEventListener("DOMContentLoaded", function (event) {
  if (checkAll() == false) {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = true;
    document.getElementsByClassName("btn btn-primary")[0].title = setButtonTooltip();
  } else {
    // Set the button class="btn btn-primary" in div class="form-actions" to enabled
    document.getElementsByClassName("btn btn-primary")[0].disabled = false;
  }
});

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