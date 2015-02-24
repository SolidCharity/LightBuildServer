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
            <li {{"class=active" if page == "projects" else ""}}><a href="/projects">Projects</a></li>
            % if page=="package":
              <li class="active"><a href="/package/{{username}}/{{projectname}}/{{packagename}}
                 % if defined("buildtarget") and defined("branchname"):
#{{branchname}}_{{buildtarget}}
                 % end
">Package {{username}}:{{projectname}}:{{packagename}}</a></li>
            % end
            <li {{"class=active" if page == "machines" else ""}}><a href="/machines">Machines</a></li>
            <li><a href="http://www.lightbuildserver.org" target="_blank">About</a></li>
          </ul>
          % if auth_username == None:
          <form class="navbar-form navbar-right" role="form" action="/login">
            <button type="submit" class="btn-xs btn-success">Login</button>
          </form>
          % end
          % if not auth_username == None:
          <form class="navbar-form navbar-right" role="form" action="/logout">
            <button type="submit" class="btn-xs btn-success">Logout{{logout_auth_username}}</button>
          </form>
          % end
        </div><!--/.navbar-collapse -->
      </div>
    </div>
