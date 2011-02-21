/* Author: 

$(document).ready(function() {
});

*/

var is_editor = false;

function ui_to_editor() {
    $("#view_title").hide();
    $("#edit_title").show();
    //$("#view_description").hide();
    $("#view_description").hide();
    $("#edit_description").show();
    $("#code").hide();
    $("#edit_code").show();
    $("#editbox").show();
    $("#subtitle").hide();
    $("#comments").hide();
    
    $("#btn_edit .ui-button-text").html("Cancel");
}

function ui_to_viewmode() {
    $("#view_title").show();
    $("#edit_title").hide();
    $("#view_description").show();
    $("#edit_description").hide();
    $("#code").show();
    $("#editbox").hide();
    $("#edit_code").hide();
    $("#subtitle").show();
    $("#comments").show();
    
    $("#btn_edit .ui-button-text").html("Edit");
}

function _toggle_ui_to_editor() {
    if (is_editor)
        ui_to_viewmode();
    else
        ui_to_editor();
    is_editor = !is_editor;
}

var previewWindow;    
function preview() {
    uri = "/preview?title=" + encodeURI($("#title").val()) + "&desc=" + encodeURI($("#desc").val())
        + "&code=" + encodeURI($("#input_code").val());
    if (previewWindow && !previewWindow.closed) {
        previewWindow.location = uri;
    } else {
        // opens a new window with the edit
        previewWindow = window.open(uri, 'mywin',
        'left=20,top=20,width=600,height=500,toolbar=0,location=0,resizable=0,menubar=0,status=0');
    }
}


function follow() {
    alert("follow");
}