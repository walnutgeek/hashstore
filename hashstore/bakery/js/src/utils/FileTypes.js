import _ from "lodash" ;
import {ValueEnum} from "./enums";
import file_types from "../../../../utils/file_types.json";


export const FileTypes = new ValueEnum( file_types,{
    findByExt(ext){
        ext = ext.toLowerCase();
        for(let k in this.k2v){
            if(this.k2v.hasOwnProperty(k)){
                let v = this.k2v[k];
                if(_.isArray(v.ext)){
                    if( v.ext.indexOf(ext) >= 0 ){
                        return k;
                    }
                }
            }
        }
        return this.BINARY;
    },
    mime(k){
        return this.k2v[k].mime;
    }
});
export default FileTypes;
