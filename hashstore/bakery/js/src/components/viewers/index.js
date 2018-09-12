import React from 'react';

import _ from 'lodash'
import Bundle from './Bundle';
import Markdown from './Markdown';
import Tabular from './Tabular';
import Text from './Text';
import Raw from './Raw';
import Download from './Download';
import { Classes, Button, ButtonGroup} from "@blueprintjs/core";
import {asBinary, asText} from '../../stores/SessionStore'
import {ViewSet} from "../../stores/ContentStore";
import ContentActions from "../../stores/ContentActions";

const viewers = { Bundle, Tabular, Markdown, Text };

const get_renderers = ( view_names ) => {
    return view_names.reduce((obj, n) =>
        Object.assign(obj, {[n]: viewers[n]}), {});
}

export const detect_viewers = ( info ) => {
    if( info.size < 100000 ){
        let accepted = [];
        _.forOwn(viewers, (v,k) =>{
           if( v.accept_types.indexOf(info.file_type) >= 0 ){
               accepted.push(k);
           }
        });
        if(accepted.length == 0){
            return new ViewSet({Raw,Download},asBinary);
        }else{
            return new ViewSet(get_renderers(accepted),asText);
        }
    }else{
        return new ViewSet({Download}, null);
    }
}


export class View extends React.Component {
    render() {
        const {path, info, viewSet} = this.props;

        const viewCount = viewSet.viewCount();
        if ( !viewCount ) {
            return <div>no views</div>;
        }
        const V = viewSet.view().render;
        const viewer = <V path={path} info={info} content={viewSet.content}/>;
        if (viewCount == 1) {
            return viewer;
        }
        return (
            <div>
                <ButtonGroup>
                    {_.map(viewSet.names, (n, i) => (
                    <Button
                    onClick={() => ContentActions.selectViewer(i)}
                    className={ viewSet.active(i) ? Classes.INTENT_PRIMARY: ""}>
                        {n}
                    </Button>))}
                </ButtonGroup>
                {viewer}
            </div>);
    }
};

