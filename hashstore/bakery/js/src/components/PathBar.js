import React from 'react';
import AltContainer from 'alt-container';
import {
  Route
} from 'react-router-dom';

import {
    Button, Popover, Classes,
    CollapsibleList, CollapseFrom, MenuItem,
    Position, PopoverInteractionKind
} from "@blueprintjs/core";
import {ToButton,ToMenuItem} from './common_componets'
import PathStore from '../stores/PathStore';
import SessionStore from '../stores/SessionStore';
import PathActions from '../stores/PathActions';
import AuthActions from '../stores/AuthActions';
import classNames from "classnames";


const Icon = ({iconName}) => (
    <span className={`pt-icon pt-icon-${iconName}`}></span>);

export const PathBar = ({match}) => {
    const {path} = match.params;
    PathActions.setPath(path);
    return (
        <AltContainer store={PathStore}>
            <PathBarBody />
        </AltContainer>);
};
export default PathBar;

const buildMenuItems = (history, path) => {
    let menuItems = [];
    if( path.settings ){
        menuItems.push(
            <MenuItem text="Settings"
                      onClick={ () => history.push("/~/") }
                      /> );
        const control = path.settings[0];
        if( control ){
            const name = control[0].toUpperCase() + control.substring(1);
            menuItems.push(
                <MenuItem text={name}
                          onClick={ () => history.push(`/~/${control}`) }
                           /> );
        }
    }else if( path.aliasPath ){
        path.aliasPath.allSubpaths().forEach(subpath=>{
            console.log(subpath.name(), subpath.toString());
            menuItems.push(<MenuItem text={subpath.name()}
                                     onClick={ ()=>history.push(`/${subpath.toString()}`) }
                                      />  );
        });
    }else{
        console.log('empty');
    }
    return menuItems;
};

class PathBarBody extends React.Component {
    render() {
        const {path} = this.props;

        return (
            <nav className="pt-navbar pt-">
                <div className="pt-navbar-group pt-align-left">
                    <Route render={({history}) => {
                        const items = buildMenuItems(history, path);
                        return (
                            <div className="pt-navbar-heading">
                                <img src="/.app/hashstore.svg"
                                     style={{width: 30, height: 30,
                                         marginRight: 10}}
                                     onClick={()=>history.push('/')}/>
                                <CollapsibleList
                                    collapseFrom={CollapseFrom.START}
                                    visibleItemCount={3}
                                    className={Classes.BREADCRUMBS}
                                    dropdownTarget={<span className={Classes.BREADCRUMBS_COLLAPSED} />}
                                    renderVisibleItem={this.renderBreadcrumb}
                                >
                                    {items}
                                </CollapsibleList>
                            </div>);
                        }}/>
                </div>
                <ToolBar/>
            </nav>);
    }

    renderBreadcrumb(props) {
        if (props.onClick != null) {
            return <a className={Classes.BREADCRUMB} onClick={props.onClick}>{props.text}</a>;
        } else {
            return <span className={Classes.BREADCRUMB}>{props.text}</span>;
        }
    }

}
//, Classes.BREADCRUMB_CURRENT)

const ToolBar = () => (
    <AltContainer store={SessionStore}>
        <ToolBarBody />
    </AltContainer>
);

class ToolBarBody extends React.Component {
    state={email: "", passwd: ""}

    componentDidMount(){
        AuthActions.fetchServerInfo();
    }

    render() {
        if (SessionStore.isAuthenticated()) {
            return (
                <div className="pt-navbar-group pt-align-right">
                    <ToButton to="/" iconName="home">Home</ToButton>
                    <ToButton to="/h/"
                              iconName="list">Potals</ToButton>
                    <span className="pt-navbar-divider"></span>
                    <Button className={Classes.MINIMAL}
                            onClick={() => AuthActions.logOut()}
                            iconName="log-out"/>
                </div>
            );

        }
        const {message, isPopoverOpen} = this.props;
        let popoverContent;
        if (message) {
            popoverContent = (
                <div className="pt-control-group pt-vertical"
                    style={{
                        width: "20em",
                        padding: "1em"
                    }}>
                    <span>{message}</span>
                </div>);
        } else {
            popoverContent = (
                <div className="pt-control-group pt-vertical"
                     style={{
                        width: "20em",
                        padding: "1em"
                     }}>
                    <div className="pt-input-group">
                        <Icon iconName="person"/>
                        <input type="text"
                               className="pt-input"
                               placeholder="Email"
                               value={this.state.email}
                               onChange={(e) => this.setState({email: e.target.value})}
                        />
                    </div>
                    <div className="pt-input-group">
                        <Icon iconName="lock"/>
                        <input type="password"
                               className="pt-input"
                               placeholder="Password"
                               value={this.state.passwd}
                               onChange={(e) => this.setState({passwd: e.target.value})}/>
                    </div>
                    <Button
                        classes={Classes.INTENT_PRIMARY}
                        onClick={() => {
                            AuthActions.logIn(this.state.email, this.state.passwd);
                            this.setState({email: "", passwd: ""});
                        }}>Login</Button>
                </div>);
        }
        return (
            <div className="pt-navbar-group pt-align-right">
                <Popover
                    content={popoverContent}
                    interactionKind={PopoverInteractionKind.CLICK}
                    isOpen={isPopoverOpen}
                    onInteraction={(open)=>AuthActions.setPopover(open)}
                    position={Position.BOTTOM_RIGHT}
                >
                    <Button className={Classes.MINIMAL}
                            iconName="log-in"/>
                </Popover>
            </div>);
    }
}
