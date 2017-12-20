function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function serverError() {
    bootbox.alert({
      size: "small",
      title: "Server error",
      message: 'An error occurred on the server.<br> Please contact the administrator: <a href="mailto:vid.podpecan@ijs.si?Subject=PMC%20search%20server%20error" target="_top">vid.podpecan@ijs.si</a>'
  });
}

$(document).ready(function () {
    // $( "#searchform" ).submit(function( event ) {
    //   alert( "Handler for .submit() called." );
    //   event.preventDefault();
    // });

    var lastQuery = '';

    $('#results').hide();
    $('#searchbutton').attr("disabled", true);


    $("#id_query").on('input',function(e){
        if($("#id_query").val().trim() != lastQuery) {
            $('#searchbutton').attr("disabled", true);
        }
        else{
            $('#searchbutton').removeAttr("disabled");
        }
    });

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", Cookies.get('csrftoken'));
            }
        }
    });

    $('#querybutton').click(function(event) {
        // event.preventDefault();

        var query = $('#id_query').val().trim();
        var stype = $('input[name=pubtype]:checked', '#searchform').val().trim();

        if(!query) {
            bootbox.alert({
              title: "Empty query!",
              message: 'Please enter a valid query.'
          });
        }
        else {
            var spinHandle = loadingOverlay().activate();

            lastQuery = query;

            var posting = $.post('ask', { 'q': query, 'st': stype} );
            posting.done(function( data ) {
                if(!data.status) {
                    bootbox.alert({
                      size: "small",
                      title: "Processing error",
                      message: data.message,
                      callback: function(){}
                  });
                }
                else{
                    // console.log(data);
                    if(!data.pmchits) {
                        bootbox.alert({
                          title: "No results!",
                          message: 'Maybe your query is invalid or no freetext articles match your query.'
                      });
                    }
                    else if(!data.indb){
                        bootbox.alert({
                          title: "No results!",
                          message: 'No articles matching the query were found in the database.<br> Maybe you should contact the administrator and ask for an update.'
                        });
                    }
                    else {
                        bootbox.alert({
                          size: 'large',
                          title: "Results",
                          message: sprintf('%d articles were found by PMC search.<br>%d are present in the database.<br><br>Click on <strong>search and export</strong> to download the corpus', data.pmchits, data.indb),
                          className: "modalSmall",
                          callback: function(){$('#searchbutton').removeAttr("disabled");}
                        });
                    }
                }
            });
            posting.fail(function() {
                serverError();
            });
            posting.always(function() {
                loadingOverlay().cancel(spinHandle);
            })
        }
    });


    $( "#searchform" ).submit(function( event ) {
        event.preventDefault();

        bootbox.confirm({
            title: "Query the database?",
            message: 'Do you want to extract and download articles matching the query?<br><br><span class="label label-info">Note</span> This may take few minutes if the result set is large.',
            buttons: {
                confirm: {
                    label: 'Yes',
                    className: 'btn-success'
                },
                cancel: {
                    label: 'No',
                    className: 'btn-danger'
                }
            },
            callback: function (result) {
                if(result)
                    search();
            }
        });
    });

    function search() {
        var spinHandle = loadingOverlay().activate();

        var query = $('#id_query').val().trim();
        var tags = $('#id_tags').val().trim();
        var ignoretags = $('#id_ignoretags').val().trim();
        var nonempty = $('#id_nonempty').is(':checked');
        var stype = $('input[name=pubtype]:checked', '#searchform').val().trim();

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
                console.log(data);
                if(!data.pmchits) {
                    $('#results').html('<hr class="style14"> <h3>No results!</h3><p>Maybe your query is invalid or no freetext articles exist.</>');
                }
                else if(!data.indb){
                    $('#results').html('<hr class="style14"> <h3>No results!</h3><p>No articles matching the query were found in the database. Maybe you should contact the administrator and ask for an update.</>');
                }
                else {
                    $('#pmchits').text(data.pmchits);
                    $('#indb').text(data.indb);
                    $('#empty').text(data.empty);
                    $('#corpuslink').attr('href', '/media/' + data.fname);
                    $('#corpuslink').text(data.fname);
                    $('#corpusinfo').text(sprintf(' (%s, %d documents)', data.fsize, parseInt(data.exported)));

                }
                $('#results').show(1000);
            }
        });
        posting.fail(function() {
            serverError();
        });
        posting.always(function() {
            loadingOverlay().cancel(spinHandle);
        })
    };

})
