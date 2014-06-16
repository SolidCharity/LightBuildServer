% include('header.tpl', title='Projects', page='projects')
    <div class="container">
      <div class="row">
	<h2>Projects</h2>
	<ul>
             % for project in sorted(projects):
		<li>Project {{project}}
                <ul>
                   % for package in sorted(projects[project]):
                        <li><a href="{{projects[project][package]['detailurl']}}">Package {{package}}</a></li>
                   % end
                </ul>
		</li>
             % end
	</ul>
      </div>
    </div>
% include('footer.tpl')
