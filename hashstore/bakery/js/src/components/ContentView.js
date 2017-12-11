import React from 'react';
import AltContainer from 'alt-container';

import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';

import WebPath from '../utils/WebPath';
import PathActions from '../stores/PathActions';
import PathStore from '../stores/PathStore';

import {
    Breadcrumb, CollapsibleList, Button,Popover,
    Classes,Position, MenuItem} from "@blueprintjs/core";

export const ContentView = ({match}) =>{
    const {path} = match.params;
    return (<AltContainer store={PathStore}>
        <ContentViewBody />
    </AltContainer>);
};


class ContentViewBody extends React.Component {
    render() {
        const {path} = this.props;
        return (
            <div>
                <h4>ContentView</h4>
                {path}
            </div>);
    }
}

export default ContentView;
