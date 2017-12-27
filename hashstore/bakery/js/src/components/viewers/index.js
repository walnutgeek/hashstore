import React from 'react';

import _ from 'lodash'
import Bundle from './Bundle';
import TextFile from './Text';
import { Classes, Button, ButtonGroup} from "@blueprintjs/core";

export const viewers = { Bundle, TextFile };

export const find_viewers = ( type ) => {
    let accepted = [];
    _.forOwn(viewers, (v,k) =>{
       if( v.accept_types.indexOf(type) >= 0 ){
           accepted.push(k);
       }
    });
    return accepted;
}

export const has_viewers = (type) => find_viewers(type).length > 0;


export const get_renderers = ( view_names ) => {
    return view_names.reduce((obj, n) =>
        Object.assign(obj, {[n]: viewers[n]}), {});
}

export class View extends React.Component {
    state = {viewer: 0}

    render() {
        const {path, info, content} = this.props;
        let viewNames = find_viewers(info.type);
        if (viewNames.length == 0) {
            return <div>no viewers</div>
        }
        const renderers = get_renderers(viewNames);
        let getV = function (viewer) {
            const V = viewer.render;
            return <V path={path} info={info} content={content}/>;
        };
        if (viewNames.length == 1) {
            return getV(renderers[viewNames[0]]);
        }
        let viewer = this.state.viewer;
        if(viewer >= viewNames.length){
            viewer = 0;
        }
        return (
            <div>
                <ButtonGroup>
                    {_.map(viewNames, (n, i) => (<Button
                        className={ i === viewer ? Classes.INTENT_PRIMARY: ""}
                        onClick={() => this.setState({viewer: i})}>{n}</Button>))}
                </ButtonGroup>
                {getV(renderers[viewNames[viewer]])}
            </div>);
    }
};

export default viewers;