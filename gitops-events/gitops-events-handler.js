
// TODO: Rewrite in Go
// Why? It should be fun

var http = require('http');
const exec = require("child_process").exec
//const request = require('sync-request');

function executeShell(command) {
    var makeProcess = exec(command,
         function (error, stdout, stderr) {
             stderr && console.error(stderr);
        });
    makeProcess.stdout.on('data', function(data) {
        process.stdout.write(data);
    });
}

http.createServer(function (req, res) {
  let body = '';
    req.on('data', chunk => {
        body += chunk.toString();
    });
    req.on('end', () => {        
        console.log(body);
        gitops_event = JSON.parse(body)
        executeShell('echo ' + gitops_event.commitid)
        res.end('ok');
    });
  res.end();
}).listen(4390); 