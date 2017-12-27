import Cake from './Cake';

export class AliasPath{
    constructor(path, slash){
        this.slash = slash || false;
        this.path = path;
    }

    child(name, slash){
        return new AliasPath([...this.path, name], slash);
    }
    isCakeBased(){
        return this.path[0] instanceof Cake;
    }

    name(){
        if( this.path.length === 1 && this.isCakeBased() ){
            return this.path[0].short();
        }
        return this.path[this.path.length-1];
    }

    subpath(i){
        if( i < this.path.length ){
            return new AliasPath( this.path.slice(0, i), true );
        }
        throw new Error( "too big i="+i+" path:"+ this.path);
    }

    allSubpaths(){
        let array = [];
        for(let i = 1 ; i < this.path.length; i++){
            array.push(this.subpath(i));
        }
        array.push(this);
        return array
    }

    toString(){
        return (this.isCakeBased() ? '_/': '') +
            this.path.map(p => p.toString()).join('/') +
            (this.slash ? '/' : '');
    }
}

export default class WebPath{
    constructor(s){
        s = s || '';
        this.path = s.split(new RegExp('/+'));
        let length = this.path.length;
        this.name = this.path[length - 1];
        this.slash = this.name === '';
        if (this.slash) {
            length = length - 1;
            this.path = this.path.slice(0, length);
            this.name = this.path[length - 1];
        }
        if (length < 1 || this.name === '') {
            this.root = true;
        } else {
            const key = this.path[0];
            if (key === '~') {
                this.settings = this.path.slice(1);
            } else {
                let alias, path_start;
                if (key === '_') {
                    alias = new Cake(this.path[1]);
                    path_start = 2;
                } else {
                    alias = this.path[0];
                    path_start = 1;
                }
                let path = this.path.slice(path_start);
                this.aliasPath = new AliasPath([alias, ...path], this.slash);
            }
        }
    }

    child(name, slash){
        return new WebPath(this.aliasPath.child(name, slash).toString());
    }

    ext(){
        if( this.slash ){
          return '/';
        }else {
            for (var i = this.name.length - 1; i > 0; i--) {
                if (this.name[i] === '.') {
                    return this.name.substr(i + 1).toLowerCase();
                }
            }
        }
        return null;
    }


    toString(){
        return this.path.join('/') +
            (this.slash ? "/" : "");
    }

}
