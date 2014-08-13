% include('header.tpl', title='Projects', page='projects')
    <div class="container">
      <div class="row">
        % for username in sorted(users):
		<h2>Projects of user {{username}}</h2>
		<ul>
	             % for project in sorted(users[username]):
			<li>Project {{project}}
                	<ul>
	                   % for package in sorted(users[username][project]):
        	                <li><a href="{{users[username][project][package]['detailurl']}}">Package {{package}}</a>
				% for buildtarget in users[username][project][package]['buildresult']:
					% if 'resultcode' in users[username][project][package]['buildresult'][buildtarget]:
					<a href="/logs/{{username}}/{{project}}/{{package}}/master/{{buildtarget}}/{{users[username][project][package]['buildresult'][buildtarget]['number']}}" class="{{users[username][project][package]['buildresult'][buildtarget]['resultcode']}}">{{buildtarget}}</a>&nbsp;
					% end
				% end
				</li>
                	   % end
	                </ul>
			</li>
	             % end
		</ul>
	% end
      </div>
    </div>
% include('footer.tpl')
