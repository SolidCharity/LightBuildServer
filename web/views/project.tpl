% include('header.tpl', title='Project', page='project')
    <div class="container">
      <div class="row">
		<h2>Details of Project {{username}}:{{project}}</h2>
		Build all packages for:
		% for buildtarget in buildtargets:
		<a href="/buildproject/{{username}}/{{project}}/{{buildtarget}}">{{buildtarget}}</a>&nbsp;
		%end
        	<ul>
	            % for package in sorted(users[username][project]):
        	        <li><a href="{{users[username][project][package]['packageurl']}}">Package {{package}}</a>
		        % for buildtarget in users[username][project][package]['buildresult']:
			   % if 'resultcode' in users[username][project][package]['buildresult'][buildtarget]:
			      <a href="/logs/{{username}}/{{project}}/{{package}}/master/{{buildtarget}}/{{users[username][project][package]['buildresult'][buildtarget]['number']}}" class="{{users[username][project][package]['buildresult'][buildtarget]['resultcode']}}">{{buildtarget}}</a>&nbsp;
			   % end
			% end
			</li>
                   % end
	        </ul>
      </div>
    </div>
% include('footer.tpl')
