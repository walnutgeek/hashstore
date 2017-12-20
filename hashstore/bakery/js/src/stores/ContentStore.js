
import alt from '../alt';
import ContentActions from './ContentActions';
import LogActions from './LogActions';
import {get_json, get} from './SessionStore'


class ContentStore {

    constructor(){
        this.path = null;
        this.info = undefined;
        this.content = undefined;

        this.bindListeners({
            handleSetPath: ContentActions.SET_PATH,
            handleSetPathInfo: ContentActions.SET_PATH_INFO,
            handleSetContent: ContentActions.SET_CONTENT,
        });

        this.registerAsync({
            requestFileInfo() {
                return {
                    remote(state) {
                        let url = state.path.aliasPath.toString();
                        if( state.path.aliasPath.isCakeBased() ){
                            url = url.substring(2);
                        }
                        return get_json('info/'+ url);
                    },
                    success: ContentActions.setPathInfo,
                    error: LogActions.logIt,
                };
            },
            requestContent() {
                return {
                    remote(state) {
                        let url = state.path.aliasPath.toString();
                        if( state.path.aliasPath.isCakeBased() ){
                            url = url.substring(2);
                        }
                        return get('data/'+ url);
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
            if( this.info.size < 100000 ){
                this.getInstance().requestContent();
            }
        }
    }


    handleSetContent(content){
        this.content = content;
    }

}

const contentStore = alt.createStore(ContentStore, 'ContentStore');
export default contentStore;