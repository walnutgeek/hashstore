import React from 'react';
import AltContainer from 'alt-container';

import {
  BrowserRouter as Router,
  Route, Link, Switch
} from 'react-router-dom';

import ContentActions from '../stores/ContentActions';
import ContentStore from '../stores/ContentStore';
import {View} from "./viewers";

import {flatMapTable} from "./common_components";

export const ContentView = ({match}) =>{
    const {path} = match.params;
    return (<AltContainer store={ContentStore}>
                <ContentViewBody />
            </AltContainer>);
};




class ContentViewBody extends React.Component {
    render() {
        const {path, info, viewSet} = this.props;
        return (
            <div>
                {info ? (
                    <div>
                        {flatMapTable(info)}
                        <View path={path} info={info} viewSet={viewSet}/>
                    </div>) : <div />}
            </div>);
    }
}



export default ContentView;
