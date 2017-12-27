import React from 'react';
import AltContainer from 'alt-container';

import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';

import ContentActions from '../stores/ContentActions';
import ContentStore from '../stores/ContentStore';
import {View} from "./viewers";

import {
    Breadcrumb, CollapsibleList,
    Button, Popover,
    Classes, Position, MenuItem
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
                 {info ? (
                     <div>
                        <table className="pt-table pt-bordered">
                            <thead>
                                <tr>
                                {Object.keys(info).map(t=><th>{t}</th>)}
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                {Object.keys(info).map(t=><td>{info[t]}</td>)}
                                </tr>
                            </tbody>
                        </table>
                        <View path={path} info={info} content={content}/>
                     </div>) : <div />}
            </div>);
    }
}



export default ContentView;
