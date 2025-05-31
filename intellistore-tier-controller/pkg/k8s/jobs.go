package k8s

import (
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// CreateMigrationJob creates a Kubernetes Job for tier migration
func CreateMigrationJob(jobName, namespace, bucketName, objectKey, fromTier, toTier, apiServiceURL string) (*batchv1.Job, error) {
	backoffLimit := int32(3)
	ttlSecondsAfterFinished := int32(3600) // 1 hour

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      jobName,
			Namespace: namespace,
			Labels: map[string]string{
				"app":         "intellistore-migration",
				"bucket":      bucketName,
				"from-tier":   fromTier,
				"to-tier":     toTier,
				"managed-by":  "tier-controller",
			},
		},
		Spec: batchv1.JobSpec{
			BackoffLimit:            &backoffLimit,
			TTLSecondsAfterFinished: &ttlSecondsAfterFinished,
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app":         "intellistore-migration",
						"bucket":      bucketName,
						"from-tier":   fromTier,
						"to-tier":     toTier,
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:  "migration",
							Image: "ghcr.io/intellistore/migration-worker:latest",
							Env: []corev1.EnvVar{
								{
									Name:  "BUCKET_NAME",
									Value: bucketName,
								},
								{
									Name:  "OBJECT_KEY",
									Value: objectKey,
								},
								{
									Name:  "FROM_TIER",
									Value: fromTier,
								},
								{
									Name:  "TO_TIER",
									Value: toTier,
								},
								{
									Name:  "API_SERVICE_URL",
									Value: apiServiceURL,
								},
							},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("100m"),
									corev1.ResourceMemory: resource.MustParse("128Mi"),
								},
								Limits: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("500m"),
									corev1.ResourceMemory: resource.MustParse("512Mi"),
								},
							},
						},
					},
				},
			},
		},
	}

	return job, nil
}