function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$(document).ready(function () {
    // $( "#searchform" ).submit(function( event ) {
    //   alert( "Handler for .submit() called." );
    //   event.preventDefault();
    // });

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
            console.log(data);
            // var content = $( data ).find( "#content" );
            // $( "#result" ).empty().append( content );
            // clearform();
        });
        posting.fail(function() {
            alert('Server error. Please contact the administrator (vid.podpecan@ijs.si)')
        });
        posting.always(function() {
            loadingOverlay().cancel(spinHandle);
        })
    });

})
