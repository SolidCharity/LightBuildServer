<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LightBuildServer: {{title}}</title>
<link href="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css" rel="stylesheet">
<script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
<script src="/ext/bootbox/bootbox.min.js"></script>

<link href="/css/main.css" rel="stylesheet">
    <script type="text/javascript">
    function init () {
       bootbox.alert("{{message}}", function() {
         window.location.href = "{{redirect}}";
       });
    }
    </script>

</head>
<body onload="init()">
    <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container-fluid">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="/">LightBuildServer</a>
        </div>
        <div class="navbar-collapse collapse">
        </div><!--/.navbar-collapse -->
      </div>
    </div>
</body>
</html>
