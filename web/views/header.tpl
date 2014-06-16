<html>
<head>
<title>LightBuildServer: {{title}}</title>
<link href="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css" rel="stylesheet">
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>

<link href="/css/main.css" rel="stylesheet">

</head>
<body>
    <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
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
            <li {{"class=active" if page == "projects" else ""}}><a href="/projects">Projects</a></li>
            % if page=="package":
              <li class="active"><a href="/detail/{{username}}/{{projectname}}/{{packagename}}">Package {{username}}:{{projectname}}:{{packagename}}</a></li>
            % end
            <li {{"class=active" if page == "machines" else ""}}><a href="/machines">Machines</a></li>
            <li><a href="http://www.lightbuildserver.org" target="_blank">About</a></li>
          </ul>
          % if username == None:
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
          % if not username == None:
          <form class="navbar-form navbar-right" role="form" action="/logout">
            <button type="submit" class="btn btn-success">Logout</button>
          </form>
          % end
        </div><!--/.navbar-collapse -->
      </div>
    </div>
