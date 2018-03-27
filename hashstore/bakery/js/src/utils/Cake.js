import factory from 'base-x';
import {TextDecoder} from 'text-encoding';

const de_utf8 = new TextDecoder("utf-8");

export const base62 = factory(  '0123456789' +
                                'abcdefghijklmnopqrstuvwxyz' +
                                'ABCDEFGHIJKLMNOPQRSTUVWXYZ');

import {IntEnum} from './enums';

export const KeyStructure = new IntEnum({
    INLINE: 0,
    SHA256: 1,
    PORTAL: 2,
    PORTAL_VTREE: 3,
    PORTAL_DMOUNT: 4,
    CAKEPATH: 5
},{displayPrefix: {
    INLINE: '=',
    SHA256: '#',
    PORTAL: '$',
    PORTAL_VTREE: '$',
    PORTAL_DMOUNT: '$',
    CAKEPATH: '>'
}});

const trimForDisplay = (s)=> s.length > 8 ? s.substring(s.length-8) : s;


export const Role = new IntEnum({
    SYNAPSE: 0,
    NEURON: 1,
});

export class CakePath {
    constructor(s , path){
        if( s instanceof Cake && _.isArray(path) ){
            this.root = s;
            this.path = path;
        }else {
            path = s.split(new RegExp('/+'));
            const l = path.length;
            if (l > 1 && path[l - 1] == '') {
                path = path.slice(0, l - 1);
            }
            if (path[0] === '') {
                this.root = new Cake(path[1]);
                this.path = path.slice(2);
            } else {
                this.root = null;
                this.path = path;
            }
        }
    }
    isRelative(){
        return !this.root ;
    }

    makeAbsolute(abspath){
        if( this.isRelative()  ){
            if(!abspath.isRelative()){
            return new CakePath( abspath.toString() + '/'
                + this.toString());
            }else{
                return null;
            }
        }
        return this;
    }

    toString(){
        let list = this.isRelative() ? this.path :
            ['', this.root.toString(), ...this.path];
        return list.join('/');
    }
}


export class Cake{
    constructor(s){
        this.s = s;
        const buf = base62.decode(s);
        const header = buf[0];
        this.keyStructure = KeyStructure.i2s[header >> 1];
        this.role = Role.i2s[header & 1];
        this.data = buf.slice(1);
    }


    static ensureCake(s){
        if( !s || s === "null" || s === "None" ){
            return null;
        }
        return new Cake(s);
    }

    displayName(){
        const ch = KeyStructure.displayPrefix[this.keyStructure];
        if( this.is_cakepath() ){
            const cp = this.cakepath();
            const path = cp.isRelative() ? cp.path:
                    [ "", cp.root.displayName() , ...cp.path]
            return ch + path.join("/");
        }
        return  ch + trimForDisplay(this.s) ;
    }

    link(cakepath){
        let cp = this.cakepath();
        if( this.is_cakepath() && cp.isRelative()){
            cp = cp.makeAbsolute(cakepath);
        }
        return "/_"+cp.toString() ;
        //TODO: rethink it's wrong to know about website url structure here, but ooh well
    }

    has_data(){
        return this.keyStructure === KeyStructure.INLINE;
    }

    is_guid(){
        return this.keyStructure === KeyStructure.PORTAL
            && this.keyStructure === KeyStructure.PORTAL_VTREE
            && this.keyStructure === KeyStructure.PORTAL_DMOUNT;
    }

    is_cakepath(){
        return this.keyStructure === KeyStructure.CAKEPATH;
    }

    cakepath(){
        if(this.is_cakepath()) {
            return new CakePath(de_utf8.decode(this.data));
        }else{
            return new CakePath(this, []);
        }
    }

    toString(){
        return this.s;
    }
}

export default Cake;
