import React from 'react';
import {
  BrowserRouter as Router,
  Route,
  Link
} from 'react-router-dom';

import Button from './Button';

const Main = () => (
  <Router>
      <div>
        <nav className="pt-navbar .modifier">
          <div className="pt-navbar-group pt-align-left">
            <div className="pt-navbar-heading">
                <img src="/.app/hashstore.svg"
                     style={{width: 30, height: 30}} />
            </div>
            <input className="pt-input pt-icon-search" placeholder="Search files..." type="text" />
          </div>
          <div className="pt-navbar-group pt-align-right"
               >
              <Button to="/" icon="home" >Home</Button>
              <Button to="/about" icon="comment" >About</Button>
              <Button to="/topics" icon="list" >Topics</Button>
            <span className="pt-navbar-divider"></span>
              <Button icon="user" />
              <Button icon="notifications" />
              <Button icon="cog" />
          </div>
        </nav>
      <div style={ {padding: "1em"}}>
          <Route exact path="/" component={Home}/>
          <Route path="/about" component={About}/>
          <Route path="/topics" component={Topics}/>
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