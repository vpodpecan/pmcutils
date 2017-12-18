function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$(document).ready(function () {
    // $( "#searchform" ).submit(function( event ) {
    //   alert( "Handler for .submit() called." );
    //   event.preventDefault();
    // });

    $('#results').hide();

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", Cookies.get('csrftoken'));
            }
        }
    });


    $( "#searchform" ).submit(function( event ) {
        event.preventDefault();

        var query = $('#id_query').val().trim();
        var tags = $('#id_tags').val().trim();
        var ignoretags = $('#id_ignoretags').val().trim();
        var nonempty = $('#id_nonempty').is(':checked');
        var stype = $('input[name=pubtype]:checked', '#searchform').val().trim();


        var spinHandle = loadingOverlay().activate();
        var posting = $.post('api', { 'q': query, 't': tags, 'it': ignoretags, 'st': stype, 'n': nonempty} );
        posting.done(function( data ) {
            if(!data.status) {
                bootbox.alert({
                  size: "small",
                  title: "Processing error",
                  message: "Message: " + data.message,
                  callback: function(){}
              });
            }
            else{
                $('#results').show(1000);
                $('#pmchits').text(data.pmchits);
                $('#indb').text(data.indb);
                $('#empty').text(data.empty);
                $('#corpuslink').attr('href', '/media/' + data.fname);
                $('#corpuslink').text(data.fname);
                $('#corpusinfo').text(' (' + data.fsize + ', ' + data.exported + ' documents)');
            }
        });
        posting.fail(function() {
            bootbox.alert({
              size: "small",
              title: "Server error",
              message: 'An error occurred on the server. Please contact the administrator: <a href="mailto:vid.podpecan@ijs.si?Subject=PMC%20search%20server%20error" target="_top">vid.podpecan@ijs.si</a>',
              callback: function(){}
          });
        });
        posting.always(function() {
            loadingOverlay().cancel(spinHandle);
        })
    });

})
