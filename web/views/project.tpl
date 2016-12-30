% include('header.tpl', title='Project', page='project')
    <div class="container">
      <div class="row">
		<h2>Details of Project {{username}}:{{project}}:{{branchname}}</h2>
        	<table class="table">
		<tr><td>Build all packages:</td>
		% for buildtarget in sorted(buildtargets):
		<td>
		<a href="/buildproject/{{username}}/{{project}}/{{branchname}}/{{buildtarget}}"><button class="btn btn-default">Build {{buildtarget}}</button></a>
		<br/>
		<a href="/rebuildproject/{{username}}/{{project}}/{{branchname}}/{{buildtarget}}"><button class="btn btn-default">Rebuild {{buildtarget}}</button></a>
                </td>
		%end
		</tr>
	            % for package in sorted(users[username][project]['Packages']):
        	        <tr><td><a href="{{users[username][project]['Packages'][package]['packageurl']}}">Package {{package}}</a></td>
			% buildresult = users[username][project]['Packages'][package]['buildresult']
		        % for buildtarget in sorted(buildtargets):
			   <td>
			   % if buildtarget in buildresult and 'resultcode' in buildresult[buildtarget]:
			      <a href="/logs/{{username}}/{{project}}/{{package}}/{{branchname}}/{{buildtarget}}/{{users[username][project]['Packages'][package]['buildresult'][buildtarget]['number']}}" class="{{users[username][project]['Packages'][package]['buildresult'][buildtarget]['resultcode']}}">{{buildtarget}}</a>
			   % end
			   </td>
			% end
			</tr>
                   % end
	        </table>
      </div>
    </div>
% include('footer.tpl')
