function get_display(project_name) {
    console.log('project display: '+ project_name);
    // send ajax POST request to start background job
    $.ajax({
        type: 'POST',
        url: Flask.url_for('phame.display', {'project':project_name}),
        success: function(data, status, request) {
          $("#output").load(Flask.url_for('phame.display', {'project':project_name}))
        },
        error: function() {
            alert('Unexpected error');
        }
    });
}

function send_notification(project) {
  console.log('email project: '+ project);
  $.ajax({
        type: 'GET',
        url: Flask.url_for('phame.notify', {'project':project}),
        success: function(data, status, request) {
          console.log('email notification sent for ' + project);
        },
        error: function() {
            alert('Unexpected error');
        }
    });
}

function send_stats(project, project_status) {
  console.log('stats for project: '+ project);
  $.ajax({
        type: 'POST',
        url: Flask.url_for('phame.add_stats'),
        dataType: "JSON",
        contentType: 'application/json;charset=UTF-8',
        data: JSON.stringify({status:project_status, project:project}, null, '\t'),
        success: function(data, status, request) {
          console.log('insert ' + project + ' status ' + project_status);
        },
        error: function() {
            alert('Unexpected error');
        }
    });
}
function update_progress(status_url, project) {
    console.log('update progress called with: ' + status_url);
    // send GET request to status URL
    console.log('project: '+ project);

    $.ajax({
        type: 'GET',
        url: status_url,
        success: function(data, status, request) {
          let result = data['Result'];
          let project_status = data['task_output'];
          console.log('url: '+status_url);
          console.log('result: '+result);
          console.log('project_status: '+project_status);
          console.log('status: '+status);
          if (result !== null) {
            console.log('result not null, sending status');
            send_stats(project, result);
          }

          let last_line;

          var promise = $.ajax(Flask.url_for('phame.get_log', {'project':project}));
          promise.done(function(data){
            console.log('last line '+ data['log']);
            last_line = data['log'];
          });
          promise.fail(function() {
            console.log('cannot get log');
          });

            if (result !== 'PENDING' && result !== 'PROGRESS')  {
                //project has finished executing
              let loading_div = document.getElementById("loading");
              let content_div = document.getElementById("content");
              loading_div.style.display = 'none';
              content_div.style.display = 'block';
              send_notification(project);
              get_display(project);
              console.log('project '+project+ ' status '+result);
            }
            // not getting status updates, so check log file
            else if (project_status === 'null' && last_line === 'null'){
              // rerun in 2 seconds
                setTimeout(function () {

                    document.getElementById("project-status").innerHTML = 'current step...unknown';
                    document.getElementById("project-time").innerHTML = 'elapsed time...unknown';

                    update_progress(status_url, project);
                }, 1000);
            }// not getting status updates, so check log file
            else if (project_status === 'null' && last_line !== 'null'){
              // rerun in 2 seconds
                setTimeout(function () {

                    document.getElementById("project-status").innerHTML = 'current step...' + last_line;
                    document.getElementById("project-time").innerHTML = 'elapsed time...unknown';

                    update_progress(status_url, project);
                }, 1000);
            }
            else {
                // rerun in 2 seconds
                setTimeout(function () {
                  console.log('project status ' + project_status);
                  let status_json = JSON.parse(project_status);
                  console.log('status_json ' + status_json);
                  console.log(status_json['status']);
                  let fields = status_json['status'].split("  ");
                  console.log('fields ' + fields);
                  let elapsed_time = fields[0].replace("b'", "");
                  console.log(elapsed_time);
                  let current_step = fields[1].slice(0, -3);
                  let detail = last_line.replace("b'", "").replace("\n", "");
                  console.log('current step ' + current_step);
                    document.getElementById("project-status").innerHTML = 'current step...' + current_step;
                    document.getElementById("project-time").innerHTML = 'elapsed time...' + elapsed_time;
                    document.getElementById("project-detail").innerHTML = 'detail...' + detail;

                    update_progress(status_url, project);
                }, 1000);
            }
        },
        error: function() {
            alert('Unexpected error');
        }
    });

}
