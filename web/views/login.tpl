% include('header.tpl', title='Project', page='project')
    <div class="container">
      <div class="row">
          <h2>Login</h2>

          % if auth_username == None:
          <form action="/do_login" method="POST">
            <div class="input-group">
              <input type="text" placeholder="Username" name="username" class="form-control">
            </div>
            <br/>
            <div class="input-group">
              <input type="password" placeholder="Password" name="password" class="form-control">
            </div>
            <br/>
            <button type="submit" class="btn btn-success">Sign in</button>
          </form>
          % end
          % if not auth_username == None:
          You are already logged in!
          % end
      </div>
    </div>
% include('footer.tpl')
