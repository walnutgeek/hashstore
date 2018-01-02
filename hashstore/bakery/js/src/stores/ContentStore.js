
import alt from '../alt';
import ContentActions from './ContentActions';
import LogActions from './LogActions';
import {get, asText, parseJSON} from './SessionStore'
import {detect_viewers} from '../components/viewers'


export class ViewSet {
    constructor(viewers, method){
        this.viewers = viewers;
        this.names = Object.keys(this.viewers);
        this.selectedView = 0;
        this.method = method;
        this.content = null;
    }

    view(){
        return this.viewers[this.names[this.selectedView]];
    }

    active(i){
        return i == this.selectedView;
    }

    viewCount(){
        return this.names.length;
    }

    selectViewer(viewer){
        if( viewer < this.names.length){
            this.selectedView = viewer;
        }
    }

    needToLoadContent(){
        return this.method != null ;
    }

}


class ContentStore {

    constructor(){
        this.path = null;
        this.info = undefined;
        this.viewSet = undefined;

        this.bindListeners({
            handleSetPath: ContentActions.SET_PATH,
            handleSetPathInfo: ContentActions.SET_PATH_INFO,
            handleSetContent: ContentActions.SET_CONTENT,
            handleSelectViewer: ContentActions.SELECT_VIEWER,
        });

        this.registerAsync({
            requestFileInfo() {
                return {
                    remote(state) {
                        const url = state.path.aliasPath.toUrl();
                        return get('info/'+ url).then(parseJSON);
                    },
                    success: ContentActions.setPathInfo,
                    error: LogActions.logIt,
                };
            },
            requestContent() {
                return {
                    remote(state, method) {
                        let url = state.path.aliasPath.toUrl();
                        return get('data/'+ url).then(method);
                    },
                    success: ContentActions.setContent,
                    error: LogActions.logIt,
                };
            },
        });
    }

    handleSetPath(path){
        this.path = path;
        this.info = null;
        this.content = null;

        if(this.path && this.path.aliasPath){
            this.getInstance().requestFileInfo();
        }
    }
    handleSetPathInfo(info){
        this.info = info;
        this.content = null ;
        if( this.info != null ){
            this.viewSet = detect_viewers(this.info);
            if( this.viewSet.needToLoadContent() ){
                this.getInstance().requestContent(this.viewSet.method);
            }
        }
    }

    handleSetContent(content){
        this.viewSet.content = content;
    }

    handleSelectViewer(viewer){
        this.viewSet.selectViewer(viewer);
    }

}

const contentStore = alt.createStore(ContentStore, 'ContentStore');
export default contentStore;