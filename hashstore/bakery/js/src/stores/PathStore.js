
import alt from '../alt';
import PathActions from './PathActions';
import AuthActions from './AuthActions';
import {get} from './SessionStore'


class PathStore {
    constructor(){
        this.path = null;

        this.bindListeners({
            handleSetPath: PathActions.SET_PATH,
            handleSetPathInfo: PathActions.SET_PATH_INFO,
        });

        this.registerAsync({
            getFileInfo() {
                return {
                    remote(state) {
                        let url = state.path.aliasPath.toString();
                        if( state.path.aliasPath.isCakeBased() ){
                            url = url.substring(2);
                        }
                        return get('info/'+ url);
                    },
                    success: PathActions.setPathInfo,
                    error: AuthActions.failedLogin,
                };
            },
        });
    }

    handleSetPath(path){
        this.path = path;
        this.info = null;
        if(this.path && this.path.aliasPath){
            this.getInstance().getFileInfo();
        }
    }
    handleSetPathInfo(info){
        this.info = info;
    }

}

const pathStore = alt.createStore(PathStore, 'PathStore');
export default pathStore;