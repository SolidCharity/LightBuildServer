% include('header.tpl', title='Project', page='project')
    <div class="container">
      <div class="row">
		<h2>Details of Project {{username}}:{{project}}</h2>
        	<table class="table">
		<tr><td>Build all packages:</td>
		% for buildtarget in buildtargets:
		<td><a href="/buildproject/{{username}}/{{project}}/{{buildtarget}}"><button class="btn btn-default">Build {{buildtarget}}</button></a></td>
		%end
		</tr>
	            % for package in sorted(users[username][project]):
        	        <tr><td><a href="{{users[username][project][package]['packageurl']}}">Package {{package}}</a></td>
		        % for buildtarget in users[username][project][package]['buildresult']:
			   <td>
			   % if 'resultcode' in users[username][project][package]['buildresult'][buildtarget]:
			      <a href="/logs/{{username}}/{{project}}/{{package}}/master/{{buildtarget}}/{{users[username][project][package]['buildresult'][buildtarget]['number']}}" class="{{users[username][project][package]['buildresult'][buildtarget]['resultcode']}}">{{buildtarget}}</a>
			   % end
			   </td>
			% end
			</tr>
                   % end
	        </table>
      </div>
    </div>
% include('footer.tpl')
