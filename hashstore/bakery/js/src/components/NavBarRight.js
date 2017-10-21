import React from 'react';
import AltContainer from 'alt-container';
import {
    Button,
    Popover,
    Classes,
    Position,
    PopoverInteractionKind,
} from "@blueprintjs/core";
import ToButton from './ToButton'
import authStore from '../stores/AuthStore';
import AuthActions from '../stores/AuthActions';

const Icon = ({iconName}) => (
    <span className={`pt-icon pt-icon-${iconName}`}></span>);

const NavBarRight = () => (
    <AltContainer store={authStore}>
        <NavBar />
    </AltContainer>
);



export default NavBarRight;

class NavBar extends React.Component {
    state={email: "", passwd: ""}

    render() {
        if (authStore.isAuthenticated()) {
            return (
                <div className="pt-navbar-group pt-align-right">
                    <ToButton to="/" iconName="home">Home</ToButton>
                    <ToButton to="/portals"
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
