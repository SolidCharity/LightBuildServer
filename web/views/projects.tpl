% include('header.tpl', title='Projects', page='projects')
    <div class="container">
      <div class="row">
        % for username in sorted(users):
		<h2>Projects of user {{username}}</h2>
		<ul>
	             % for project in sorted(users[username]):
			<li><a href="/project/{{username}}/{{project}}">Project {{project}}</a>
                	<ul>
	                   % for package in sorted(users[username][project]):
        	                <li><a href="{{users[username][project][package]['packageurl']}}">Package {{package}}</a></li>
                	   % end
	                </ul>
			</li>
	             % end
		</ul>
	% end
      </div>
    </div>
% include('footer.tpl')
