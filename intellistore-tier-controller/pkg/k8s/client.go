package k8s

import (
	"fmt"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

// NewClient creates a new Kubernetes client
func NewClient(kubeconfig string) (kubernetes.Interface, error) {
	var config *rest.Config
	var err error

	if kubeconfig != "" {
		// Use provided kubeconfig file
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
	} else {
		// Use in-cluster config
		config, err = rest.InClusterConfig()
	}

	if err != nil {
		return nil, fmt.Errorf("failed to create Kubernetes config: %w", err)
	}

	client, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kubernetes client: %w", err)
	}

	return client, nil
}