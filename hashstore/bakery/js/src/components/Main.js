import React from 'react';
import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';


import PathBar from './PathBar';
import ContentView from './ContentView';
import AliasSettings from './AliasSettings';
import AclSettings from './AclSettings';

const Home = ()=>(
    <div>
        <h3>Home</h3>
        <Link to="/~/aliases" >List of aliases</Link> <br />
        <Link to="/~/acl" >List of cakes from ACLs</Link>
    </div>
);

const Stub = () => {
    return (<h1>Stub</h1>);
};

//ContentView
const Main = ()=>(
    <Router>
        <div>
            <Switch>
                <Route path="/:path*" component={PathBar}/>
            </Switch>
            <div style={ {padding: "1em"}}>
                <Switch>
                    <Route exact path="/" component={Home}/>
                    <Route path="/~/acl" component={AclSettings}/>
                    <Route path="/~/aliases" component={AliasSettings}/>
                    <Route path="/:path*" component={ContentView}/>
                </Switch>
            </div>
        </div>
    </Router>
);

export default Main