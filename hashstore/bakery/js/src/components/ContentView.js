import React from 'react';
import AltContainer from 'alt-container';

import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';

import ContentActions from '../stores/ContentActions';
import ContentStore from '../stores/ContentStore';

import {
    Breadcrumb, CollapsibleList, Button,Popover,
    Classes,Position, MenuItem
} from "@blueprintjs/core";

export const ContentView = ({match}) =>{
    const {path} = match.params;
    return (<AltContainer store={ContentStore}>
                <ContentViewBody />
            </AltContainer>);
};


class ContentViewBody extends React.Component {
    render() {
        const {path, info, content} = this.props;
        return (
            <div>
                <h4>ContentView</h4>
                <div id="2" > {info ? (<pre>
{JSON.stringify(info, undefined, 2)}
{JSON.stringify(JSON.parse(content),undefined, 2)}
</pre>) : <span />} </div>
            </div>);
    }
}



export default ContentView;
