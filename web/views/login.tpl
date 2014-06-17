<html>
<head>
<title>LightBuildServer: {{title}}</title>
<link href="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css" rel="stylesheet">
<script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>

<link href="/css/main.css" rel="stylesheet">

</head>
<body>
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
          <ul class="nav navbar-nav">
          % if auth_username == None:
          <form class="navbar-form navbar-right" role="form" action="/do_login" method="POST">
            <div class="form-group">
              <input type="text" placeholder="Username" name="username" class="form-control">
            </div>
            <div class="form-group">
              <input type="password" placeholder="Password" name="password" class="form-control">
            </div>
            <button type="submit" class="btn btn-success">Sign in</button>
          </form>
          % end
          % if not auth_username == None:
          <form class="navbar-form navbar-right" role="form" action="/logout">
            <button type="submit" class="btn-xs btn-success">Logout</button>
          </form>
          % end
        </div><!--/.navbar-collapse -->
      </div>
    </div>
</body>
</html>
