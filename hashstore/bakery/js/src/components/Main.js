import React from 'react';
import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';

import {Button,Popover,Classes,Position} from "@blueprintjs/core";
import NavBarRight from './NavBarRight';


const Public = () => <h3>Public</h3>
const Protected = () => <h3>Protected</h3>

const Main = () => (
  <Router>
      <div>
        <nav className="pt-navbar .modifier">
          <div className="pt-navbar-group pt-align-left">
            <div className="pt-navbar-heading">
                <img src="/.app/hashstore.svg"
                     style={{width: 30, height: 30}} />
            </div>
          </div>
          <NavBarRight/>
        </nav>
      <div style={ {padding: "1em"}}>
          <Switch>
              <Route path="/portals/:portalId" component={Protected}/>
              <Route path="/portals" component={Protected}/>
              <Route path="/" component={Public} />
          </Switch>
      </div>
    </div>
  </Router>
)


const Home = () => (
  <div>
    <h2>Home</h2>
  </div>
)

const About = () => (
  <div>
    <h2>About</h2>
  </div>
)

const Topics = ({ match }) => (
  <div>
    <h2>Topics</h2>
    <ul>
      <li>
        <Link to={`${match.url}/rendering`}>
          Rendering with React
        </Link>
      </li>
      <li>
        <Link to={`${match.url}/components`}>
          Components
        </Link>
      </li>
      <li>
        <Link to={`${match.url}/props-v-state`}>
          Props v. State
        </Link>
      </li>
    </ul>

    <Route path={`${match.url}/:topicId`} component={Topic}/>
    <Route exact path={match.url} render={() => (
      <h3>Please select a topic.</h3>
    )}/>
  </div>
)

const Topic = ({ match }) => (
  <div>
    <h3>{match.params.topicId}</h3>
  </div>
)

export default Main