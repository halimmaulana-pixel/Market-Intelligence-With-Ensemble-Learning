import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, background: '#fff3f3', borderRadius: 8, margin: 16 }}>
          <h3 style={{ color: '#c62828' }}>Error saat render halaman:</h3>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 8, color: '#333' }}>
            {this.state.error.toString()}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}
