import React from 'react';
import {
  Router, Route, Switch
} from 'react-router-dom';


import PathBar from './PathBar';
import ContentView from './ContentView';
import AliasSettings from './AliasSettings';
import AclSettings from './AclSettings';
import history from '../history'
import {ToLink} from "./common_componets";

const Home = ()=>(
    <div>
        <h3>Home</h3>
        <ToLink to="/~/aliases" >List of aliases</ToLink> <br />
        <ToLink to="/~/acl" >List of cakes from ACLs</ToLink>
    </div>
);

const Stub = () => {
    return (<h1>Stub</h1>);
};

//ContentView
const Main = ()=>(
    <Router history={history}>
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